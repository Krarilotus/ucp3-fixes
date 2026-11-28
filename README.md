# ucp3-fixes

Bug fixes for Stronghold Crusader / Crusader Extreme 1.41, packaged as eight
independently selectable UCP3 modules, plus four configuration plugins: UCP3
Fixes, which turns the fixes on, and the UCP3 setup family (UCP3 Basics, UCP3
Basics + Fixes, UCP3 Recommended). Every fix module is off by default. The hop farm
fix was created by Daniel Fleger (Samurai, Discord: D. Daniel). AIV Troop
Behaviour builds on his original module and is mainly authored by Krarilotus. Fixed
Engineers is maintained by UCP contributors. Each packaged module includes
`CREDITS.md`; original authorship and licenses stay with their owners. Worker Delivery Fix is a code-reviewed preview awaiting in-game
acceptance.

Fixed Engineers 0.2.0 is merged into this repository. Its signed
[test package](https://github.com/UnofficialCrusaderPatch/UCP3-extensions-store/releases/download/fixed-engineers-test-0.2.0-merged/fixed-engineers-ucp3.0.7-test-0.2.0-merged.zip)
and [3.0.7 store PR](https://github.com/UnofficialCrusaderPatch/UCP3-extensions-store/pull/42)
are available, but in-game acceptance is still pending. It replaces the crew
and equipment-command corrections from the older Unit Behaviour Fixes preview;
disable that preview before selecting Fixed Engineers. Tunneler behaviour belongs
to Improved Tunnelers and starting troops to AI Swapper.

| Module | Scope |
| --- | --- |
| [hopfarm-limit-fix](hopfarm-limit-fix/) | Counts hops against the existing shared AIV farm limit. Long-term economy effects still need gameplay testing. |
| [AI: AIV Troop Behaviour](aiv-troops-behaviour/) | Optional initial digging/defense assignments and defensive hold/patrol controls for 15 troop types, including slaves, with global defaults and per-AI AIC overrides. Includes the row 9/11/18 loading fix. |
| [Fixed Engineers](docs/fixed-engineers.md) | Corrects siege crew cleanup, safe dismounting, and catapult/trebuchet attack-order stopping. In-game acceptance of this combined module remains pending. |
| [Worker Delivery Fix](docs/worker-delivery.md) | Lets workers deliver to reachable granaries and armories when the keep route is blocked, and prevents AI from removing otherwise valid stores for that reason. Stockpiles use a different native check. In-game acceptance is pending. |
| [Gatehouse Capture Fix](docs/gatehouse-capture.md) | Counts living troops, but not dying troops, for gatehouse capture and defense. In-game acceptance is pending. |
| [Hunter Targeting Fix](docs/hunter-targeting.md) | Lets hunters choose nearby deer and approach along their native path when a shot is blocked. In-game acceptance is pending. |
| [Scenario Settings Fix](docs/scenario-settings.md) | Keeps the troops, weapons and goods a map forbids in the scenario editor forbidden in skirmish, multiplayer, trail and Play a Map games. Not part of the UCP3 Fixes plugin. In-game acceptance is pending. |
| [Build Over Workers](build-over-workers/) | By Monsterfish (GPL-3.0): place buildings and walls over your own (optionally allied) workers, who step aside to a free tile instead of being removed; AI walls move people aside too. Writes no save data. |
| [Route Search](route-search/) | Not a fix: the one owner of a unit's route search. Other modules' route policies (Smarter Pathing's assassin shortcut, Gatehouse Fixes' gate routes) run there in a fixed order, so they work together. No settings; alone it changes nothing. Its README documents the policy contract. MIT. |
| [Full Minimap](full-minimap/) | Not a fix: shows the whole map on the minimap on every map size, with the visible-area frame, clicks and unit orders scaled to match. Off until its option is ticked. English texts only. Not part of the UCP3 Fixes plugin. In-game check of the Alt+R dot mode is pending. |

## UCP3 Fixes plugin

[UCP3 Fixes](ucp3-fixes/) is a plugin: dependencies and suggested values, no code.
It selects the six fix modules above plus
[Interface and Visual Fixes](https://github.com/Krarilotus/extension-interface-visual-fixes)
and [Audio Fixes](https://github.com/Krarilotus/extension-audio-fixes) and suggests
their bug fixes on. Interface and Visual Fixes' two interface features and its Ghost
Objects repair are left as they are. Suggested values stay editable in Customizations.
It needs launcher 1.0.16 or later, because AIV Troop Behaviour 0.3.0 does. Gatehouse
Fixes (`smarter-gatehouses`) is not a dependency: it has no license yet and is not in
the public Store.

## UCP3 setup family

Three plugins form the `ucp3` family, each in a top-level folder as the Store recipe's
`location` requires. They need launcher 1.0.17 or later (family support); 1.0.16 lists
them in the Store but rejects them at install.

| Package | Family label | Selects |
| --- | --- | --- |
| [ucp3-basics](ucp3-basics/) (root) | Basics | UCP2 Legacy Defaults and Graphics API Replacer; no settings |
| [ucp3-basics-fixes](ucp3-basics-fixes/) | Basics + Fixes | UCP3 Basics and UCP3 Fixes |
| [ucp3-recommended](ucp3-recommended/) | Recommended | UCP3 Basics, UCP3 Fixes, ConqueringArabia, Build Over Workers (all switches on) and Interface and Visual Fixes' lobby map descriptions and Load in the skirmish lobby |

Basics has no configuration demands, so it never claims the family slot when another
member depends on it. The members differ only in modules that write no save data: a
save made with one member loads and keeps playing under the others (tested on Crusader
and Extreme 1.41). None of them adds snow textures or gameplay rebalancing;
Recommended's Build Over Workers placement can be switched off.

The [extension ownership review](docs/extension-ownership.md) maps related
gatehouse, tunneler, stable, building, projectile, texture and AI work to its
existing owner. Improved Tunnelers remains its own module. Gatehouse Fixes is its
own module too; its hooks and controls are not copied into this repository. Stables
work remains outside UCP3 Fixes until its complete implementation is published and
reviewed.

## Installation and configuration

Install signed packages through the extension store once published. For local
testing, use a module ZIP from Releases if one is available, or create one by
zipping that module folder's contents. `definition.yml` must be at the ZIP root.
GitHub's repository-level **Download ZIP** is a source archive, not an installable
module package. There may be no published releases yet.

Place each module ZIP in `ucp/modules/<name>-<version>.zip`. Unsigned local modules require
the launch option **Disable Security**. Plugins (UCP3 Fixes and the UCP3 family) go to
`ucp/plugins/<name>-<version>.zip`, which the launcher unpacks, and need no signature. Select the module in Content, then use its
settings under **AI → AIV Troop Behaviour** for troop controls, **AI → Fixes**
for the hop farm fix, or **Bugfixes** for Fixed Engineers, Worker Delivery Fix, Gatehouse Capture Fix, Hunter Targeting Fix and Scenario Settings Fix. Changing a switch
requires restarting the game. Every fix is off by default, so selecting a module
alone keeps the game's behaviour until you switch its fix on; the AIV module's
additional troop controls are opt-in too. The modules are not selected by default.

Each module uses `core` and therefore has type `module`, not `plugin`. Their
`UCP2Switch` controls follow the established AI or Bugfixes categories.
The fixes remain independently selectable. The AIV module's additional behaviour
controls are opt-in and require aicloader, but no AI-swapping module. See its
README for the Customizations defaults, AIC precedence and release limitations.

Descriptions and option labels cover all nine frontend languages: English,
German, French, Russian, Hungarian, Turkish, Chinese, Spanish and Persian.
English and the root `description.md` provide fallback for other languages.
Keep `description.md` identical to `locale/description-en.md`; tests check this
because the installed-extension reader does not automatically fall back to the
English locale description.

An unsupported or conflicting executable causes a descriptive initialization
error before any patch writes. UCP's `core.AOBScan` throws when no match exists;
these modules do not silently report success with a missing fix.

## Store integration

The actual store recipe is named `recipe.yml`. Use one entry per module or plugin
with a string `contents.source.location` pointing to its top-level subfolder, for
example `location: hopfarm-limit-fix` or `location: ucp3-recommended`;
`location.root` is not supported by the 3.0.7 builder. Plugins are packaged as
their whole folder (no `files.yml`) and need no signature.
Pin `github-sha` to the reviewed commit and match the version in `definition.yml`.
The 3.0.7 store recipe lists all nine supported languages. Installed
Customizations load their translations from each package.
Each module's `files.yml` keeps unrelated repository files out of its package.

## Validation

Build local test packages with:

```sh
python tools/build_modules.py --output ./local-packages
```

The builder follows each `files.yml` and writes explicit ZIP directory entries.
The frontend requires the `locale/` entry to discover translations; files under
that path alone are insufficient. Install the unsigned ZIPs in `ucp/modules`.
Use Disable Security for local testing, then select the modules in Content.

See [the review and test matrix](docs/validation.md). Run the portable regression
suite with `python -m unittest discover -s tests -v` after installing
`tests/requirements.txt`. No game binaries are distributed with the tests.

[Package authorship, translated tags and family boundaries](docs/package-metadata.md)
are documented separately. `tools/build_modules.py` also packages the four
plugin folders.
