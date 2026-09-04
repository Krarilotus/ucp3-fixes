# ucp3-fixes

Bug fixes for **Stronghold Crusader / Crusader Extreme**, packaged as UCP3 modules.
Each fix is a self-contained module in its own subfolder with its own `definition.yml`.

Author: **Samurai** (Discord: D. Daniel).

## ⚠️ Installing — use the Releases, not "Download ZIP"

**Do not** use GitHub's green **Code → Download ZIP** button. That wraps everything in a
sub-folder, so `definition.yml` no longer sits at the zip root and UCP3 shows nothing in the
Content tab.

Instead, grab the ready-made package from the [**Releases**](../../releases) page — each module
is zipped with `definition.yml` at the root — and drop the `.zip` unextracted into your
`ucp/modules/` folder. Enable **"Disable Security"** in the Launch tab while the modules are
unsigned. (Once merged into the extension store they install straight from the GUI.)

## Fixes

| Module | What it fixes |
|--------|---------------|
| [`hopfarm-limit-fix`](hopfarm-limit-fix/) | Hop farms were not counted against the AI's AIV farm limit, so the AI over-built them. Adds hops to the farm-count range check. |
| [`aiv-troop-spot-fix`](aiv-troop-spot-fix/) | AI start troops placed in AIV section-2012 rows 9, 11 and 18 were discarded on load, so they never walked to their positions (most visibly the Arabic lords' troops). Removes the three skip jumps so all rows load. |

Each module is type **module** (needs `core` access) and locates its patch site via AOB
scan, so it fails cleanly on unsupported game versions instead of corrupting memory.

## Store / installation

Each subfolder is a standalone module. In the UCP3 extension store recipe, one entry per
module points at this repo with `location.root` set to the module's subfolder. For local
testing, zip a subfolder's contents (with `definition.yml` at the zip root) into
`ucp/modules/<name>-<version>.zip` and enable "Disable Security" while unsigned.
