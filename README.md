# ucp3-fixes

Bug fixes for Stronghold Crusader / Crusader Extreme 1.41, packaged as six
independently selectable UCP3 modules. An optional UCP3 Fixes bundle selects
Worker Delivery, Gatehouse Capture, Hunter Targeting and the external Gatehouse
Fixes module together. This expanded bundle is an integration test candidate,
pending Gatehouse Fixes' upstream review and composition acceptance. The hop farm
and AIV troop modules were created by Samurai (Discord: D. Daniel); Fixed
Engineers is maintained by UCP
contributors. Worker Delivery Fix is a code-reviewed preview awaiting in-game
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

The [UCP3 Fixes bundle](ucp3-fixes/) contains dependency metadata and translated
descriptions, not copies of the fixes. Its four dependencies still own their
native code and independent settings. Gatehouse Fixes' corrections default ON
under Bugfixes; its optional stairs rules default OFF under Balance Changes.
The original package ID `smarter-gatehouses` is preserved. UCP 3.0.7 shows the packages
separately. Compatible fixes should remain independently selectable; the
[family-metadata correction](https://github.com/Krarilotus/ucp3-fixes/pull/9)
keeps them outside configuration families.
Selecting the bundle activates all four. Selecting a member alone activates
only that fix.

The [extension ownership review](docs/extension-ownership.md) maps related
gatehouse, tunneler, stable, building, projectile, texture and AI work to its
existing owner. Improved Tunnelers remains its own module. Gatehouse Fixes is
selected through its existing package dependency; its hooks and controls are
not copied into this repository. Stables work remains outside the bundle until
its complete implementation is published and reviewed.

## Installation and configuration

Install signed packages through the extension store once published. For local
testing, use a module ZIP from Releases if one is available, or create one by
zipping that module folder's contents. `definition.yml` must be at the ZIP root.
GitHub's repository-level **Download ZIP** is a source archive, not an installable
module package. There may be no published releases yet.

Place each ZIP in `ucp/modules/<name>-<version>.zip`. Unsigned local packages require
the launch option **Disable Security**. Select the module in Content, then use its
settings under **AI → AIV Troop Behaviour** for troop controls, **AI → Fixes**
for the hop farm fix, or **Bugfixes** for Fixed Engineers, Worker Delivery Fix, Gatehouse Capture Fix and Hunter Targeting Fix. Changing a switch
requires restarting the game. Simple fixes default to on when their module is
selected; the AIV module's additional troop controls are opt-in. The modules are
not selected by default.

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

The actual store recipe is named `recipe.yml`. Use one entry per module with a
string `contents.source.location` pointing to its subfolder, for example
`location: hopfarm-limit-fix`; `location.root` is not supported by the 3.0.7 builder.
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
