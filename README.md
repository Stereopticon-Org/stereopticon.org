# stereopticon.org

The website for the Stereopticon projects (wiz3D, Stereo Loom and the Stereopticon launcher), including the wiz3D game compatibility list.

The site is a single static page, built and deployed to GitHub Pages by GitHub Actions. The game list lives in this repository as one YAML file per game, so every change has a history and goes through a pull request.

## Layout

| Path | What it is |
|---|---|
| `index.html` | The whole site: home, compatibility list, game pages, API support, fix guide and 3D outputs. |
| `games/<slug>.yml` | One file per game. The file name is the game's URL: `games/left-4-dead-2.yml` is `stereopticon.org/#game-left-4-dead-2`. |
| `games/_excluded.yml` | Games left out on purpose, with the reason. |
| `shots/<slug>/` | Stereo screenshots for a game. |
| `brand/` | Official logo files (SVG and PNG). Served at `stereopticon.org/brand/`. See `LOGOS.md` for how they may be used. |
| `scripts/build_site.py` | Validates the game files and builds `_site/`. |
| `scripts/apply_report.py` | Turns an approved test report into changes to a game file. |
| `scripts/import_readme.py` | One-off import from the old tables in wiz3D's README. |
| `.github/ISSUE_TEMPLATE/compat-report.yml` | The "Game test report" form. |
| `.github/workflows/pages.yml` | Validates pull requests; builds and deploys the site on every push to `main` and once a day. |
| `.github/workflows/report-to-pr.yml` | Opens a pull request when a report gets the `approved` label. |

## A game file

```yaml
name: Left 4 Dead 2
api: DX9                 # DX7, DX8, DX9, DX10/11, DX12, Vulkan, OpenGL, HD3D
source: injector         # injector, hd3d, 3dv-direct, 3dv-auto, ogl-qb
status: mostly           # working, mostly, partial, broken, untested
install:
- Stereo-Injector/DX9/32-bit
iz3d_profile: true
notes: Only tested single player. Use `-insecure` to avoid a VAC ban.
checks:                  # optional; drives the completeness bar. good, partial or bad
  Scene depth: good
  HUD and menus: partial
shots:                   # optional; files live in shots/left-4-dead-2/
- file: issue-12-1.png
  layout: lr             # lr, rl (cross-eyed), tb, lrl (Parallel + Cross)
  issue: 12
reports:                 # added automatically from approved test reports
- issue: 12
  date: '2026-11-08'
  by: someone
  version: 0.4.3
  output: HalfSBS
  result: Mostly working
  notes: Crosshair sits at screen depth.
```

`notes` is the maintained summary that shows at the top of the game page. Reporters' own words stay under `reports`, so a single report never overwrites the summary.

## How a test report reaches the site

1. A player opens a **Game test report** issue. The "Report a result" button on each game page fills in the game and folder.
2. A maintainer reads it and adds the `approved` label.
3. The `report-to-pr` workflow updates `games/<slug>.yml` (status, checklist, the report itself), copies any attached screenshots into `shots/<slug>/`, and opens a pull request that closes the issue.
4. Merge the pull request. The site rebuilds and deploys in about a minute.

To change anything else, edit the YAML file on GitHub and open a pull request. The **Edit on GitHub** link on each game page goes straight to the file.

## Release progress

The API support page shows progress bars for the milestones in `Stereopticon-Org/wiz3D`. Each bar is closed issues out of all issues in the milestone. The daily build refreshes them. To track more repositories, add them to `MILESTONE_REPOS` in `scripts/build_site.py`.

## One-time setup

1. **Settings → Pages → Build and deployment → Source:** GitHub Actions.
2. **Settings → Pages → Custom domain:** `stereopticon.org`, then tick **Enforce HTTPS** once the certificate is issued.
3. **DNS for stereopticon.org:** `A` records for `185.199.108.153`, `185.199.109.153`, `185.199.110.153` and `185.199.111.153`, plus a `CNAME` for `www` pointing to `stereopticon-org.github.io`. GitHub's Pages docs list the current addresses, so check them there.
4. **Settings → Actions → General → Workflow permissions:** allow GitHub Actions to create pull requests.
5. **Labels:** create `compat-report` and `approved`.

## Working locally

```sh
pip install pyyaml
python scripts/build_site.py          # writes _site/
cd _site && python -m http.server     # open http://localhost:8000
```

## Licences

- Site code (`index.html`, `scripts/`, workflows): MIT, see `LICENSE`. The logos inside `index.html` are not covered; see `LOGOS.md`.
- Game data, notes and screenshots (`games/`, `shots/`): CC BY 4.0, see `LICENSE-DATA.md`.
- Logos and project names: all rights reserved, with the uses allowed in `LOGOS.md`.
- wiz3D and the Stereopticon launcher are LGPL-2.1. Stereo Loom is MIT.
