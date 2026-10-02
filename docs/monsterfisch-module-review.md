# Monsterfisch module review

Reviewed the 16 public repositories on 2 October 2026. Fourteen are related to
Stronghold; two are Minecraft projects. This is a source and package review,
not native gameplay, editor, performance or replay acceptance.

The small package corrections have upstream PRs. Native integration gaps below
remain unfinished. No new module was silently added to the Fixes bundle.

On 3 October the user authorized merging fitting source changes into the
unreleased Fixes repository. Bundle 0.1.2 selects Worker Delivery, Hunter
Targeting, Gatehouse Capture, Gatehouse Fixes, Fixed Engineers and AI Hop Farm
Counting. Implementation and controls stay with their existing owners.
AI troop behavior, tunnelers, input/graphics tools, save management and content
themes remain standalone Store packages. Attack Move and Smarter Recruits also
remain standalone: their mixed features and state/command concerns need separate
acceptance before any small correction joins the bundle.

The Gatehouse, Attack Move and Recruit PRs now flatten one-switch groups, remove
repeated explanations and prune unused locale keys. Config paths, defaults and
independent switches are unchanged. Recruit diagnostics belongs to Miscellaneous;
corrections use Bugfixes, AI counting uses AI > Fixes, optional conveniences use
Quality of Life, and gatehouse stairs use Balance Changes. These are the current
Legacy category identities, not new categories or changes to Legacy itself.
Source integration is not Store approval or native gameplay acceptance.

## Placement and ownership

| Repository | Home and boundaries | Review outcome |
| --- | --- | --- |
| SmarterGatehouses | Gatehouse Fixes. Corrections fit Bugfixes; optional stairs fit Balance Changes. The module keeps its ID. | Existing [PR #2](https://github.com/Monsterfisch/SmarterGatehouses/pull/2) provides nine-language packaging. Keep native movement/gate logic there. This repo's dead-unit capture fix remains a separate census correction. |
| ImprovedTunnelers | Independent tunneler behavior module. AI starting units stay in AI Swapper; AI quotas/strategy stay in AIC Tactics. | Existing [PR #1](https://github.com/Monsterfisch/ImprovedTunnelers/pull/1) owns 1.7.2 and its saved collapse/route state. Do not copy it into Engineers or Fixes. The reported settings/load crash needs the exact spin-off build and reproduction. |
| AttackMove | Command/waypoint extension. Separable vanilla waypoint fixes can join Fixes after acceptance; Alt stacking remains optional. | [PR #2](https://github.com/Monsterfisch/AttackMove/pull/2) adds concise translations and standard packaging. Input/cursor/command and transient route-state boundaries still need review. |
| smarter-recruits | Recruit rally and stance behavior. Separate verified corrections from added behavior. | [PR #2](https://github.com/Monsterfisch/smarter-recruits/pull/2) localizes controls and native tips, separates categories and disables diagnostics by default. Coordinate group creation with troop-behavior/AIC owners; do not duplicate their census or quotas. |
| resolution-based-zoom | Optional interface/graphics extension; Custom Hotkeys owns bindings. | [PR #2](https://github.com/Monsterfisch/resolution-based-zoom/pull/2) removes its private input dispatcher and generated duplicate. Requires [Custom Hotkeys #14](https://github.com/Krarilotus/extension-custom-hotkeys/pull/14). Display action and ladder remain in Zoom. |
| resource-grid-overlay | Map-editor/interface visualization. Custom Hotkeys owns bindings; winProcHandler owns Windows messages; render/screen observers need their proper owner. | [PR #2](https://github.com/Monsterfisch/resource-grid-overlay/pull/2) fixes packaging, translations and its unsupported numeric control. The private input and shared screen-hook collision remain open. |
| Stronghold_Crusader_Autosave | Save-management extension. Native save, UI, file and configuration responsibilities retain their existing owners. | [PR #2](https://github.com/Monsterfisch/Stronghold_Crusader_Autosave/pull/2) adds standard sliders, dependencies, translations and native-language buttons. Failed-save/rotation and file-path safety remain open. |
| exe-value-patcher-1.0.0 | Advanced executable-value tool, outside Fixes. Reuse Balance/Legacy controls where they already own a value. | [PR #2](https://github.com/Monsterfisch/exe-value-patcher-1.0.0/pull/2) separates values.yml from UCP config.yml and fixes package text. Raw addresses and mismatch writes remain a release blocker. |
| Build-over-Workers | Optional placement/relocation behavior, not an automatic Fixes dependency. | Public repository is empty. The supplied chat fragment is insufficient for a whole-module audit. Verify worker relocation, full footprints, crowded destinations and normal soldier blocking when complete source is published. |
| smarter-buildings | Split verified entrance/production corrections from optional stable production/balance changes. | Public repository is empty; renamed from Stronghold-crusader-various-production-fixes-and-features. No published stable source can be reviewed. Delivery's route-origin correction already belongs to Worker Delivery Fix. |
| Conquering Arabia | Texture/theme content using the existing files module. | [PR #2](https://github.com/Monsterfisch/ConqueringArabia_-fixed_updated_StrongholdCrusader_texture-/pull/2): concise nine-language overview; assets and credits preserved. |
| Conquering Europe | Alternative texture/theme content using files. | [PR #3](https://github.com/Monsterfisch/ConqueringEurope_-Stronghold1_textures-/pull/3): same description correction. |
| Conquering Christmas | Alternative winter texture/theme content using files. | [PR #2](https://github.com/Monsterfisch/ConqueringChristmas_-Stronghold1_textures-with-snow-/pull/2): same description correction. |
| StrongholdsOfConquest_ | AI castle/AIV and AIC content, through existing castle/AIC file owners. | Published root is an archive/content collection, not a UCP runtime module. README includes an AIC setup and texture archives; split these by existing provider before assigning families. |
| Conquest_ and optifine | Minecraft | Outside UCP. |

## Source concerns that remain

**Exe Value Patcher:** its configuration contains raw executable addresses and
defaults `skip_mismatched` to false. Image-range checks do not prove the intended
instruction or ABI, and a mismatch is explicitly allowed to proceed. The new
values.yml filename fixes a real UCP configuration collision; it does not resolve
these bindings. Do not remove checks or advertise broad executable support while
those writes remain.

**Autosave:** the assembly routine rotates older autosaves before calling the
game's save action. Rotation can remove the oldest copy and rename newer ones
before the new save succeeds; failed operations are logged and the routine
continues. This needs a recoverable save/rotation sequence through the responsible
owner, not another private save bridge. Its manual PE/import/export resolver,
ANSI file operations, separate settings file and custom dialog hooks also need
comparison with the actual supported owner APIs. Calling the native save action
is useful evidence, not proof of save, non-ASCII-path or Recorder compatibility.

**Grid Overlay and Zoom:** Grid directly patches the native Windows-message arm.
The existing winProcHandler API already provides registered priority and
CallNextProc. Zoom's input is now moved to Custom Hotkeys; Grid's remains open.
Both retain a screen-change observer at the same native site. The existing
first-wins behavior can lose one module's invalidation/reset callback. Move that
observation into a common existing lifecycle owner after proving its API gap.
Render buffer bounds/format and frame cost still need evidence.

**Attack Move:** its private LAST buffer stores unit/group/UID/tick/coordinates
used in route construction. **Smarter Recruits:** MARKS, FOLLOW_UIDS and position/
idle buffers influence rally behavior. Neither source establishes a full
save/load/new-world/replay lifecycle for those buffers. Native UID checks help
with reused IDs but do not prove state restoration or replay equivalence. Prefer
native state; distinguish disposable bookkeeping from persistent simulation data
before deciding whether any existing state provider is needed.

Smarter Recruits patches group creation and rally/stance behavior, so it must
coordinate with AIV Troop Behaviour, AIC Tactics and any shared lifecycle consumer.
The portrait PNG/render implementation also needs a demonstrated UI-owner API
gap before it is treated as a justified separate implementation. This review
does not assert that a suitable accelerated renderer already exists.

Gatehouse Fixes still needs optional-hook preflight, native hook/unload ownership,
bounded restoration and performance acceptance. Existing binding/span evidence
is described in [extension ownership](extension-ownership.md); it does not prove
whole-game composition.

Improved Tunnelers 1.7.2's state header already says ordinary settings are not
saved. Saved identity includes source fingerprint and installed native
capabilities. It also stores the radius of an unfinished collapse. Investigate
the actual spin-off/version and each changed option before blaming a settings
fingerprint or removing validation. A controlled rejection must not become an
uncaught exception or partially loaded native world.

## Reuse and package corrections

Custom Hotkeys parent `844d54d` already owns profiles, conflict checks, capture,
context and input routing. Its missing capabilities were wheel impulses and two
optional view-action callbacks. PR #14 adds those to the existing owner, without
a new input hook or speculative action registry. Ctrl+wheel is consumed only by
an eligible bound action; plain wheel, absent providers and unsuitable contexts
pass through. The catalog stays valid without Zoom. Existing profiles preserve
explicit choices; older custom profiles leave new actions unbound.

For the remaining display call, inspected ui 1.0.1 and graphicsApiReplacer at
`473774d`: their public APIs do not export resolution-step/apply. Zoom therefore
retains the game's video-options apply action through framework AOB/exposeCode,
with strengthened identifying context. The local SHC/Extreme 1.41 pair supports
that switch-context observation; this is static binding evidence only.

Autosave and Smarter Recruits reuse textResourceModifier 0.3.0 at `5ab58fa`:
GetLanguage and TransformText select CR.TEX's language and encode its text.
Translation occurs at framework afterInit, after text loading. There is no
private encoder, new save hook or gameplay tracking array introduced by these
label changes.

The live launcher registry has nine languages: de, en, fr, ru, hu, tr, ch, es,
fa. All new description/option catalogs cover it. Relevant native labels cover
the eleven game languages, including Italian and Polish. Descriptions are brief
overviews; detailed behavior and credits stay in READMEs. Existing category
identities follow the live Legacy/GUI catalog, including its current English
fallback; no duplicate translated category is invented.

The actual GUI control factory has Slider/NumberInput, not Number. The affected
numeric controls now use Slider. Standard sparse config defaults match option
defaults. Exe Value Patcher's data moved to values.yml, preserving its bytes and
custom external paths, leaving config.yml to UCP. Runtime allowlists exclude
bench/research Python. The original mechanics and explicit configuration values
remain intact; recruit diagnostics now default OFF in runtime and UI.

## Families and release status

Use the Fixes dependency bundle for compatible corrections, keeping each owner
individually selectable. Do not make independent fixes mutually exclusive
siblings. Native code stays in its module; the bundle supplies dependencies.

The Conquering packs are theme alternatives, using files. There is no published
common Conquering provider/root to reuse. A future exclusive family must use the
actual GUI family/content contract; do not invent a provider or copy resources to
Fixes just to create a heading. Related independent tools use discovery categories
and tags. AI castle configurations belong to their existing castle/AIC providers.

Checks performed: all 631 Custom Hotkeys component tests passed in Lua 5.4 and
LuaJIT; Zoom's offline resolution/native-Z/reset checks passed; nine packages
passed locale-presence checks, and six runtime packages passed YAML/default,
actual-control-type, locale-reference, Lua syntax and runtime-allowlist checks.
The eleven native label catalogs passed strict game-codepage encoding checks.
No native UI, gameplay, save/replay, graphics or performance acceptance was done
for these new changes. Human translation review and installed long/RTL layouts
remain pending. Multiplayer testing belongs to players.

The texture-description PRs are documentation-only and ready for review.
Runtime/package PRs remain draft pending their stated acceptance and native gaps.
PR #14 CI passes. Mergeability is a Git result, not a release-quality guarantee.
