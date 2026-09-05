# ucp3-fixes

Bug fixes for Stronghold Crusader / Crusader Extreme 1.41, packaged as two
independent UCP3 modules. Author: Samurai (Discord: D. Daniel).

| Module | Scope |
| --- | --- |
| [hopfarm-limit-fix](hopfarm-limit-fix/) | Counts hops against the existing shared AIV farm limit. Long-term economy effects still need gameplay testing. |
| [aiv-troop-spot-fix](aiv-troop-spot-fix/) | Restores rows 9, 11 and 18. Adds opt-in experimental global troop defaults and per-AI AIC overrides for initial digging/defense and holding/patrolling slots, including slaves. |

## Installation and configuration

Install signed packages through the extension store once published. For local
testing, use a module ZIP from Releases if one is available, or create one by
zipping that module folder's contents. `definition.yml` must be at the ZIP root.
GitHub's repository-level **Download ZIP** is a source archive, not an installable
module package. There may be no published releases yet.

Place each ZIP in `ucp/modules/<name>-<version>.zip`. Unsigned local packages require
the launch option **Disable Security**. Select the module in Content, then use its
enable switch under **AI → Fixes**. Changing a switch requires restarting the game.
The switch defaults to on for a selected module, preserving 0.1.0 behavior;
omitting `enabled` from an existing configuration also means on. The modules are
not selected by default. A plugin can set `<module-name>.enabled` to `false`.

Each module uses `core` and therefore has type `module`, not `plugin`. The
`UCP2Switch` options follow the AI/Fixes presentation used by `ucp2-legacy`.
The fixes remain independently selectable. The AIV module's additional behavior
controls are opt-in and require aicloader, but no AI-swapping module. See its
README for the Customizations defaults, AIC precedence and release limitations.

English and German descriptions and option labels are included. Other GUI
languages use English option fallback and the root `description.md` fallback.
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
The 3.0.7 store recipe currently lists only `en` under `supported-languages`;
German store descriptions require adding `de` there as a separate store change.
Each module's `files.yml` keeps unrelated repository files out of its package.

## Validation

See [the review and test matrix](docs/validation.md). Run the portable regression
suite with `python -m unittest discover -s tests -v` after installing
`tests/requirements.txt`. No game binaries are distributed with the tests.
