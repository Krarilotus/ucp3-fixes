# Fixes bundle and related extension owners

UCP3 Fixes combines compatible corrections through dependencies. Each existing
module keeps its native code and settings. Improved Tunnelers remains an independent
module: selecting Fixes must not silently enable extra tunneler abilities.

This is an ownership review of the public Monsterfisch repositories on 2 October
2026, not a claim that their gameplay or cross-module composition has passed.
The 0.1.1 integration candidate adds Gatehouse Fixes through its existing
`smarter-gatehouses: ^1.0.3` dependency. It remains a test candidate pending
upstream review and composition acceptance; no external native code is copied.

## Where the code belongs

| Change | Implementation owner | Selection and integration |
| --- | --- | --- |
| Dead troops affecting gate capture/defense | `gatehouse-capture-fix` in this repository | Existing default-on Fixes bundle member |
| Gate closing, enemy-gate routes, optional gate stairs | [Gatehouse Fixes](https://github.com/Monsterfisch/SmarterGatehouses), package ID `smarter-gatehouses` | Existing module dependency in the 0.1.1 test candidate; each switch remains configurable and stairs stay opt-in |
| Tunneler digging, target selection, collapse, terrain cleanup and raid participation | [Improved Tunnelers](https://github.com/Monsterfisch/ImprovedTunnelers) | Keep its own module and test package; no mandatory Fixes dependency |
| AI starting troop counts and initial acquisition/assignment | [AI Swapper](https://github.com/UnofficialCrusaderPatch/extension-aiSwapper) | AI Swapper owns the native initialization consumer, including tunnelers |
| Siege crew identity, death, fire, dismount and ordinary command stopping | `fixed-engineers` in this repository | Existing independent module; candidate for the bundle after its acceptance |
| AI recruitment roles, siege placement, harassment and resource payment | [AIC Tactics](https://github.com/UnofficialCrusaderPatch/extension-aic-tactics) | AI policy and per-AI AIC overrides stay with that owner |
| Delivery to granary/armory with a blocked keep route | `worker-delivery-fix` in this repository | Already a bundle member. Compare any new implementation here before adding another hook |
| Hunter deer targeting and approach | `hunter-targeting-fix` in this repository | Already a bundle member; unrelated new hunter combat rules need separate scope |
| Hop farms counted against the existing farm limit | `hopfarm-limit-fix` in this repository | Existing independent module; candidate after gameplay acceptance |
| AIV troop behavior and per-AI assignments | `aiv-troops-behaviour` in this repository | Keep its independent selection and AIC controls; do not force optional AI behavior through Fixes |
| Building entrances not refreshed when blocked | Building entrance/pathing owner, after tracing the trigger | New fix candidate; distinct from delivery's choice of route origin |
| Building over workers and safe relocation | Existing Build Over Workers implementation, after lifecycle review | Optional placement capability. Do not copy its work into delivery or gatehouse code |
| Native four-horse cap defect | Existing stable implementation, if a defect is verified | Potential default-on correction; separate from new production rules |
| Continued horse production, slowdown and timer | Stable behavior extension | Optional gameplay change with separate controls; outside the basic Fixes bundle |
| Projectile settings preventing save loads; mangonel firing outside range | Existing Custom Projectiles/equipment command owners | Trace the actual defect there. Avoid duplicate save hooks or attack-order workarounds in Fixes |

## Families, bundles and themes

Use a dependency bundle for corrections that can run together. The GUI's
configuration-family design is being reviewed for alternatives; independently
selectable fixes must not become mutually exclusive choices. PR
[#9](https://github.com/Krarilotus/ucp3-fixes/pull/9) removes their existing family
declarations; it is merged at `44bf48a`. This review neither duplicates that
metadata patch nor edits its branch.
The inspected GUI discovery `groupFamilies` implementation is currently a view
projection; it does not itself activate dependencies or prove compatibility.

Use families for actual configurations of the same content/provider, and existing
discovery tags/categories for related independent packages. Do not invent a
provider or preset merely to make a family header appear.

| Monsterfisch repository | UCP placement |
| --- | --- |
| `SmarterGatehouses` (created 1 October 2026) | Independent gatehouse module; related to Fixes, with optional balance controls |
| `ImprovedTunnelers` (created 24 September 2026) | Independent tunneler module; no ownership transfer to Fixes |
| [Attack Move](https://github.com/Monsterfisch/AttackMove) (created 2 October 2026) | Independent troop-command extension. Keep optional Alt behavior outside the basic Fixes bundle; input/command composition needs its own review |
| [Conquering Arabia](https://github.com/Monsterfisch/ConqueringArabia_-fixed_updated_StrongholdCrusader_texture-) | Existing texture extension, using the existing files owner |
| [Conquering Europe](https://github.com/Monsterfisch/ConqueringEurope_-Stronghold1_textures-) | Existing texture extension, using the existing files owner |
| [Conquering Christmas](https://github.com/Monsterfisch/ConqueringChristmas_-Stronghold1_textures-with-snow-) | Existing texture extension, using the existing files owner |
| [Strongholds of Conquest](https://github.com/Monsterfisch/StrongholdsOfConquest_) | AI castle/AIV content. Audit actual provider/preset packages before defining a castle family |
| `Conquest_` and the `optifine` fork | Minecraft content; outside UCP |

The three Conquering texture repositories are related themes, not bug fixes.
Keep them out of Fixes. Their manifests currently depend on `files`; no common
Conquering provider/root is present in the inspected packages. Reuse existing
texture content discovery. If exclusive theme selection or per-player texture
composition is introduced, implement it through the existing texture/files owner,
not through Fixes or a new private resource loader.

No public Build Over Workers or stable repository was found in the eight public
repositories initially returned for Monsterfisch; the later inventory also includes
AttackMove. The stables implementation has not yet been published, as confirmed
by the user. The chat's additional changes remain
review candidates until their complete sources are available; the supplied worker
`init.lua` alone cannot establish assembly, packaging or lifecycle safety.

For the reported optional horse-refill timing and progress display, **Stable
Production** is a descriptive name. Any verified native horse-cap/lifecycle fix
should be separately configurable under Bugfixes; production slowdown, delay caps
and added behavior belong under Balance Changes and remain opt-in. Exact source,
ownership and defaults cannot be finalized from the chat summary alone.

## Gatehouse composition evidence and remaining checks

Smarter Gatehouses upstream `71cd94c` patches detection in
`updateGateDrawBridgeOpenCloseLogic`, the pathfinding call from
`setDestinationForUnit`, and optional cursor/tribe-move/passage sites. This repo's
`gatehouse-capture-fix/capture.lua` patches troop eligibility at the native
occupancy census. The signatures identify different sites; do not combine the
implementations simply because both mention gatehouses.

A task-local real-image Lua admission check on the local SHC/Extreme 1.41 pair
also confirms the two default/five stairs-enabled hook spans do not overlap the
capture-fix span. All seven default/13 full-feature signatures have unique matches
in those fixtures. Allocation/assembly were mocked: this is binding/span evidence,
not execution of pathfinding, a load-order test or whole-game composition acceptance.

Legacy `port/o_responsivegates.lua` owns closing range/time. Smarter Gatehouses
reads the range operand in place, so its centering calculation can use that setting
without copying it. This source inspection is not a load-order/gameplay test.
Ordinary route modifications must also compose with Worker Delivery's native
path calls and with other consumers such as Improved Tunnelers.

Smarter Gatehouses still needs native binding ambiguity checks, complete preflight
for its optional stairs hooks, safe unload ownership, bounded gate/link restoration
and performance acceptance. Its machine-specific bench and non-failing failure
reports are not a release gate. [Upstream PR #2](https://github.com/Monsterfisch/SmarterGatehouses/pull/2)
provides packaging/localization and concrete pending checks without changing its
native implementation.

Improved Tunnelers [PR #1](https://github.com/Monsterfisch/ImprovedTunnelers/pull/1)
already owns its packaging, translations, native terrain correction and saved
collapse state. Reuse that PR instead of opening a competing port. Its pending
single-player game/editor/save/replay/performance acceptance and Map Extensions
prerequisite remain explicit.

Before adding an external package to the bundle:

- [ ] Review and pin the actual owner revision and dependency versions.
- [ ] Preflight enabled hooks, including conflicts and both load orders.
- [ ] Keep simple fixes ON, optional capabilities OFF, and explicit user choices intact.
- [ ] Verify package inputs, all current UI languages and established categories.
- [ ] Check normal Crusader/Extreme gameplay, save/load and matching-setup replay.
- [ ] Check maps remain usable/editable when optional modules are absent.
- [ ] Measure affected route/placement work; a dynamic signature is not performance evidence.

Multiplayer testing remains player-owned. Acceptance gaps stay open; a bundle
dependency or installable ZIP does not turn an untested module into a release.
