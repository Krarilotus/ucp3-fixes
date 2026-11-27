"""Load route-search's init.lua under Lua 5.4 with `core` backed by a flat byte image, and run
the code it writes (plus small test policies) in unicorn. Nothing in route-search is mocked;
only the framework's memory functions are."""
from pathlib import Path
import re
import struct

from lupa.lua54 import LuaRuntime
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                               UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_ESP,
                               UC_X86_REG_EIP)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'route-search'
MASK = 0xFFFFFFFF

# How UCP 3.0.7 hands one module to another (content/ucp/code/main.lua: `p = p or { public
# = {}, proxy = {} }`, then extensions/proxies.lua ExtensionProxy): calls are made on the
# module itself, enable/disable/init are hidden, and a method returning a table is wrapped
# read-only unless its name is in the module's proxy `ignored` list. Without that list the
# framework iterates nil and the launch stops. Written from that behaviour for these tests.
FRAMEWORK_PROXY = '''
local function contains(list, value)
  for _, item in pairs(list) do
    if item == value then return true end
  end
  return false
end
local function readOnly(object)
  if type(object) ~= "table" then return object end
  return setmetatable({}, {
    __index = function(_, key) return readOnly(object[key]) end,
    __newindex = function(_, key) error("Setting a value on this table is not allowed. Key: " .. tostring(key)) end,
    __pairs = function()
      return function(_, key)
        local nextKey, value = next(object, key)
        if value ~= nil then return nextKey, readOnly(value) end
      end, nil, nil
    end,
    __ipairs = function()
      return function(_, index)
        index = index + 1
        local value = object[index]
        if value ~= nil then return index, readOnly(value) end
      end, nil, 0
    end,
  })
end
return function(module, second)
  local p = second or { public = {}, proxy = {} }
  local options = p.proxy or { ignored = {} }
  return setmetatable({}, {
    __index = function(_, key)
      if key == "enable" or key == "disable" or key == "init" then return nil end
      local value = module[key]
      if type(value) == "table" then return readOnly(value) end
      if type(value) == "function" then
        return function(_, ...)
          local result = value(module, ...)
          if type(result) == "table" and contains(options.ignored, key) == false then
            return readOnly(result)
          end
          return result
        end
      end
      return value
    end,
    __newindex = function(_, key) error("Setting a value on this extension is not allowed. Key: " .. tostring(key)) end,
  })
end
'''
REGS = {'eax': UC_X86_REG_EAX, 'ebx': UC_X86_REG_EBX, 'ecx': UC_X86_REG_ECX,
        'edx': UC_X86_REG_EDX, 'esi': UC_X86_REG_ESI, 'edi': UC_X86_REG_EDI,
        'ebp': UC_X86_REG_EBP, 'esp': UC_X86_REG_ESP}


def pattern_regex(pattern):
    return re.compile(b''.join(b'.' if token == '?' else re.escape(bytes([int(token, 16)]))
                               for token in pattern.split()), re.DOTALL)


class Space:
    """One flat address range: the executable image at `base`, then heap and stack."""

    def __init__(self, image, base, size=0x400000):
        self.base, self.size = base, size
        self.memory = bytearray(size)
        self.memory[:len(image)] = image
        self.image_end = base + len(image)
        self.heap = (self.image_end + 0xFFFF) & ~0xFFFF
        self.stack_top = base + size - 0x1000

    def offset(self, address, count=1):
        offset = address - self.base
        if not 0 <= offset <= self.size - count:
            raise AssertionError('access outside the test address space: 0x%X' % address)
        return offset

    def read(self, address, count):
        offset = self.offset(address, count)
        return bytes(self.memory[offset:offset + count])

    def write(self, address, data):
        offset = self.offset(address, len(data))
        self.memory[offset:offset + len(data)] = data

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def put32(self, address, value):
        self.write(address, struct.pack('<I', value & MASK))

    def put16(self, address, value):
        self.write(address, struct.pack('<H', value & 0xFFFF))

    def allocate(self, size):
        address = self.heap
        self.heap = (self.heap + size + 0xF) & ~0xF
        return address


class RouteSearch:
    """route-search's init.lua with core backed by a Space."""

    def __init__(self, space, hooks=True):
        self.space = space
        self.scans, self.code_writes, self.data_writes, self.allocations = [], [], [], []
        self.stub_writes = []
        self.logs, self.after_init = [], []
        lua = self.lua = LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        g.INFO, g.WARNING, g.ERROR = 'INFO', 'WARNING', 'ERROR'
        g.log = lambda level, message: self.logs.append((level, message))
        if hooks:
            hook_table = lua.table()
            hook_table.registerHookCallback = lambda name, fn: self.after_init.append((name, fn))
            g.hooks = hook_table
        core = lua.table()
        core.AOBScanUnique = self.aob_scan_unique
        core.readInteger = lambda address: struct.unpack('<i', space.read(int(address), 4))[0]
        # RPS pushes *(BYTE*) for readByte (unsigned).
        core.readByte = lambda address: space.read(int(address), 1)[0]
        core.writeCodeBytes = self.write_code_bytes
        core.writeCode = self.write_code
        core.writeInteger = self.write_integer
        core.allocate = self.allocate
        core.allocateCode = self.allocate_code
        g.core = core
        # core.itob as in framework 3.0.7 core.lua.
        lua.execute('function core.itob(value) return { (value >> 0) & 0xFF, (value >> 8) & 0xFF, '
                    '(value >> 16) & 0xFF, (value >> 24) & 0xFF } end')
        loaded = lua.execute((MODULE / 'init.lua').read_text(encoding='utf-8'))
        self.module, self.options = loaded if isinstance(loaded, tuple) else (loaded, None)
        # Other modules reach it as the framework does: main.lua defaults the second return
        # value to { public = {}, proxy = {} } and wraps the module in its ExtensionProxy.
        self.api = lua.execute(FRAMEWORK_PROXY)(self.module, self.options)

    # core
    def find_all(self, pattern):
        return [self.space.base + m.start()
                for m in pattern_regex(pattern).finditer(bytes(self.space.memory))]

    def aob_scan_unique(self, pattern):
        self.scans.append(('AOBScanUnique', pattern))
        hits = self.find_all(pattern)
        if not hits:
            return None, 'not found'
        if len(hits) != 1:
            return None, 'found more than once'
        return hits[0], None

    def flatten(self, values):
        """Bytes of a code table as core.compile reads it: numbers and nested tables."""
        out = []
        for i in range(1, len(values) + 1):
            item = values[i]
            out.extend(self.flatten(item) if self.lua.eval('type')(item) == 'table' else [int(item) & 0xFF])
        return out

    def flat(self, values):
        """core.writeCodeBytes and core.allocateCode(table) do not compile: bytes only."""
        for i in range(1, len(values) + 1):
            if self.lua.eval('type')(values[i]) == 'table':
                raise AssertionError('nested table where 3.0.7 takes plain bytes')
        return values

    def write_code_bytes(self, address, values):
        self.write_code(address, self.flat(values))

    def write_code(self, address, values):
        data = bytes(self.flatten(values))
        address = int(address)
        # Only writes into the executable image count as patches; the stub lives in allocated code.
        if address < self.space.image_end:
            self.code_writes.append((address, data))
        else:
            self.stub_writes.append((address, data))
        self.space.write(address, data)

    def write_integer(self, address, value):
        address = int(address)
        if address < self.space.image_end:
            raise AssertionError('writeInteger into the executable image at 0x%X' % address)
        self.data_writes.append((address, int(value) & MASK))
        self.space.put32(address, int(value))

    def allocate(self, size, zero=None):
        address = self.space.allocate(int(size))
        self.space.write(address, bytes(int(size)))
        self.allocations.append(('data', address, int(size)))
        return address

    def allocate_code(self, values):
        if isinstance(values, int):
            address = self.space.allocate(values)
            self.allocations.append(('code', address, values))
            return address
        data = bytes(self.flatten(self.flat(values)))
        address = self.space.allocate(len(data))
        self.space.write(address, data)
        self.allocations.append(('code', address, len(data)))
        return address

    # enable() is called by the framework on the module itself; everything else the way other
    # modules call it, through the framework proxy (colon calls on modules["route-search"]).
    def enable(self):
        self.module.enable(self.module, self.lua.table())

    def call(self, method, *args):
        return self.api[method](self.api, *args)

    def add(self, policy_id, order):
        slots = self.call('addPolicy', self.lua.table_from({'id': policy_id, 'order': order}))
        return int(slots['next']), int(slots['unit'])

    def enable_policy(self, policy_id, entry):
        self.call('enablePolicy', policy_id, entry)

    def policies(self):
        listed = self.call('policies')
        count = self.lua.eval('function(t) return #t end')(listed)
        return [dict(id=listed[i]['id'], order=listed[i]['order'], entry=listed[i]['entry'],
                     next=listed[i]['next']) for i in range(1, count + 1)]

    def fire_after_init(self):
        for name, fn in self.after_init:
            assert name == 'afterInit'
            fn()


# Small test policies, hand-assembled (see the disassembly checks in the tests).
def d(value):
    return struct.pack('<I', value & MASK)


def recording_policy(unit, nxt, log, count):
    """Order-200 style: note [unit], then hand the same call on (tail jump to [next])."""
    return (b'\xA1' + d(unit) +                # mov eax, [unit]
            b'\x8B\x15' + d(count) +           # mov edx, [count]
            b'\x89\x04\x95' + d(log) +         # mov [log + edx*4], eax
            b'\xFF\x05' + d(count) +           # inc dword [count]
            b'\xFF\x25' + d(nxt))              # jmp dword [next]


def comparing_policy(nxt):
    """Order-100 style: two candidate searches through [next] with esi = PathFindingState
    (as Smarter Pathing does); returns the sum of both results."""
    return (b'\x53' b'\x56' b'\x8B\xF1' +      # push ebx / push esi / mov esi, ecx
            b'\xFF\x74\x24\x10' * 2 +           # push dword [esp+0x10] (canClimb, owner)
            b'\x8B\xCE' b'\xFF\x15' + d(nxt) +  # mov ecx, esi / call dword [next]
            b'\x8B\xD8' +                       # mov ebx, eax
            b'\xFF\x74\x24\x10' * 2 +
            b'\x8B\xCE' b'\xFF\x15' + d(nxt) +
            b'\x01\xD8' b'\x5E' b'\x5B' b'\xC2\x08\x00')  # add eax, ebx / pop esi / pop ebx / ret 8


def reentering_policy(at, head, nxt, other_unit, unit, log, flag):
    """The first time: calls the redirected search once more for another unit (as a nested
    setDestinationForUnit would) and notes [unit] after it. Every time: tail-calls [next].
    `at` is where this code is placed (for the relative call)."""
    test = b'\x83\x3D' + d(flag) + b'\x00'      # cmp dword [flag], 0
    first = (b'\xC7\x05' + d(flag) + d(1) +     # mov dword [flag], 1
             b'\x56' +                          # push esi
             b'\xBE' + d(other_unit) +          # mov esi, other
             b'\x6A\x00' b'\x6A\x07')           # push 0 / push 7
    call_at = at + len(test) + 2 + len(first)
    first += b'\xE8' + d(head - (call_at + 5))  # call head
    first += (b'\x5E' +                         # pop esi
              b'\xA1' + d(unit) +               # mov eax, [unit]
              b'\xA3' + d(log))                 # mov [log], eax
    return (test + b'\x75' + bytes([len(first)]) +  # jne pass
            first + b'\xFF\x25' + d(nxt))       # pass: jmp dword [next]


class Emulator:
    """Runs a Space in unicorn; the game's search is replaced by a recorder."""

    def __init__(self, space, search, unit_slot, results):
        self.space, self.search, self.unit_slot = space, search, unit_slot
        self.results = list(results)
        self.calls = []
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(space.base, space.size)
        uc.mem_write(space.base, bytes(space.memory))
        uc.hook_add(UC_HOOK_CODE, self.native_search, begin=search, end=search)

    def native_search(self, uc, address, size, user):
        esp = uc.reg_read(UC_X86_REG_ESP)
        word = lambda a: struct.unpack('<I', uc.mem_read(a, 4))[0]
        self.calls.append(dict(ecx=uc.reg_read(UC_X86_REG_ECX), owner=word(esp + 4),
                               climb=word(esp + 8), unit=word(self.unit_slot)))
        uc.reg_write(UC_X86_REG_EAX, self.results.pop(0) & MASK if self.results else 0)
        uc.reg_write(UC_X86_REG_EDX, 0xDEADBEEF)   # the game's search uses edx freely
        uc.reg_write(UC_X86_REG_ESP, esp + 12)
        uc.reg_write(UC_X86_REG_EIP, word(esp))

    def u32(self, address):
        return struct.unpack('<I', self.uc.mem_read(address, 4))[0]

    def run(self, start, until, regs, stack=()):
        uc = self.uc
        sp = self.space.stack_top
        for value in reversed(list(stack)):
            sp -= 4
            uc.mem_write(sp, d(value))
        for name, value in regs.items():
            uc.reg_write(REGS[name], value & MASK)
        uc.reg_write(UC_X86_REG_ESP, sp)
        uc.emu_start(start, until, count=10000)
        if uc.reg_read(UC_X86_REG_EIP) != until:
            raise AssertionError('stopped at 0x%X, not 0x%X' % (uc.reg_read(UC_X86_REG_EIP), until))
        return {name: uc.reg_read(reg) for name, reg in REGS.items()}, sp
