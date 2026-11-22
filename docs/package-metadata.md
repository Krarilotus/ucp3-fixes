# Package authorship and discovery

The runtime manifest is `definition.yml` (singular). Keep original author names
and licenses. Packaged `CREDITS.md` files distinguish original work, UCP
integration, assets and reference research; they do not assign a new license.
Daniel Fleger's (Samurai's) Hop Farm module and Monsterfish's Gatehouse module
retain their authorship. AIV Troop Behaviour lists Krarilotus as main author and
Daniel Fleger as original author. Fixed Engineers retains its collective author and credits its actual
implementation; np123's historical patch is research, not copied production code.

Tags use the existing launcher topic IDs and flat `tags.<id>` locale keys in all
nine registered languages. The Hotkeys and Fixed Engineers metadata reuse their
existing reviewed discovery branches. Derived capabilities are generated from
package contents by the Store owner; they are not hand-written into manifests.

UCP3 Fixes 0.2.0 is a plugin with dependencies and suggested values only, and no
`family` membership. The fix modules ship vanilla defaults (off); the plugin
turns their fixes on. The fixes themselves remain individually selectable and
have no `family` membership either.

The `ucp3` family consists of three plugins owned by this repository: UCP3 Basics
(root, the same two packages as the previous first-install default, no
configuration demands), UCP3 Basics + Fixes
and UCP3 Recommended. They are alternative configurations of one setup, so a
family fits; their members may differ only in modules without save data. Each
member's locale files carry `family.ucp3: UCP3`, its configuration label
(`family.ucp3.configuration`) and its `tags.<id>` labels in all nine languages.
Tags come from the established vocabulary (modpack, bugfixes, textures,
interface). Families describe alternative configurations, not independent fixes,
tools or shared file dependencies. Improved Tunnelers, AI behavior, interface
tools and themes stay separate.

Store PR #55 reuses the existing PR #33 discovery exporter, including verified
cached-archive metadata. It does not change that owner's branch or publish the
Store. Patch versions distinguish changed package manifests from older signed
test archives; simulation code, options and assets are unchanged.

Validation uses the actual preview GUI dependency parser, tag localization,
search and family projection, plus focused package checks. This does not replace
installed UI or pending gameplay/save/editor/replay/performance acceptance.
