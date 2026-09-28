# v2.2 — decisions taken while building

Nobody is awake during this run. Every time the brief, the Danish spec and this repo disagree — or say
nothing — the phase picks the option that best fits the plan and writes one line here, prefixed with its
phase id. Newest at the bottom.

The decisions v2.0 took are in `docs/UI_PLAN.md` §2 (D1–D16) and v2.1's are in
`docs/v2_1/DECISIONS.md`; both still hold unless a line below replaces one.

---

- **W1** — **The kunnat a project serves are read off the spatial index, and the index is inverted
  once.** `properties.kunnat` is a Danish field; no Finnish project carries one, which is why *Areas
  served* was empty on all 169 project sheets and the Municipalities column of Data › Projects was
  empty on every row. `dist/infra_index.json` already answers the question the other way round
  (`kunta:091 → [project ids]`), so `infraKomIndex()` inverts it once into `id → {kunta codes}` and
  caches that — the Pipeline table asks for it 169 times per render, and a scan of the whole index per
  row is the kind of thing that only shows up on a slow machine. The cache is dropped when
  `dist/infra.json` lands with a fuller index. 157 of the 169 projects now name at least one kunta;
  the other twelve have no published alignment at all and say **"Not covered yet"** rather than
  drawing an empty list.
- **W1** — **A project with neither line, area nor point frames Finland and says why.** The mini map
  was created with Denmark's own centre (`[56, 10.5]` is Jutland) and only moved once `fitBounds`
  found something, so a project with no geometry opened on another country. Every map in this build
  now starts at `FI_CENTER`, the centre of `FI_BOX`, and the three states are said apart: still
  loading, "no alignment — the municipalities it serves are framed instead", and "Not covered yet".
- **W1** — **The projects CSV gains a `postinumerot` column, from the same index.** The sheet already
  listed the postal codes a project runs through; the export named only the kunnat. The column is
  added after `kunnat` rather than in place of it, so a file written before tonight still parses by
  name. No other export changed.
- **W1** — **A year is a label, not a quantity: one `fmtYear()`.** `Year built` was `fmt: "int"`, so
  fi-FI's thousands space made the buildings legend read `1 987 — 2 000`. The fix is a `year` entry in
  both `FMT` and `FMT_TIGHT` plus the building popup's Completed row — one function, and the map
  legend, the bins and the popup cannot disagree again. `nf(v, 0)` stays right for a count of
  dwellings, which *is* a quantity.
- **W1** — **The chart's title and sub-title are clipped by measurement, not by a character count.**
  The chart is a 1 200-unit SVG built as a string and rasterised straight to PNG, so the text cannot
  wrap by itself and cannot be measured in the document — an indicator description simply ran off the
  right edge and into the downloaded file. One reused 2-D canvas measures the same font, the line is
  cut on a word with an ellipsis, and the **full** string stays in the element's `<title>`: hover on
  screen, and nothing is lost from the export. Wrapping to a second line was the alternative and was
  rejected: the line chart's plot area starts at y = 84 and a second sub-title line would have had to
  push every chart's geometry down for the longest description in the registry.
- **W1** — **The build line reads one `APP_VERSION`.** It said `v2.0` a whole release after v2.1
  shipped because the string lived in the footer's markup. A check asserts the line and the constant
  agree, so the next release cannot ship the previous one's number.
- **W1** — **README's screenshot is build output now.** It was still the v2.0 look because it was made
  by hand. `tests/ui_v2.spec.py` writes `docs/screenshot.png` from the same map-at-1440 shot it already
  takes for `docs/ui_v2/`, so the two cannot drift. (`docs/ui_v2/*.png` stays uncommitted; this one
  file is committed because README embeds it.)
- **W1** — **`Oulun normaalikoulu` is moved by an override file, and the page says so.** The register's
  own coordinate for oppilaitosnumero 00599 is 60.158409, 24.958738 — central Helsinki, 540 km from
  the school it names — so the school sat on Helsinki's map and in Helsinki's benchmark. The
  replacement is 65.057742, 25.464132, which is not typed in from an address but taken from a dataset
  already on disk: OpenStreetMap's `amenity=school` "Oulun normaalikoulun lukio" in this dashboard's
  own public-buildings layer (`dist/public/564.json`). `data/external/overrides/schools.csv` is the
  one place a school coordinate may be corrected and it corrects nothing else — no name, no type, no
  figure — and the school sheet prints the source of a replaced coordinate under Sources.
- **W1** — **The override is applied twice, from one file, because `build_schools.py` cannot run
  tonight.** That script re-fetches the whole register over the network and writes `data/processed/`,
  which this run may not touch. So `build_schools.py` gained the permanent fix (the override is
  applied *before* the point-in-polygon placement, so kunta, postal code and osa-alue all follow from
  the corrected point), and `build_dashboard.py` applies the same CSV to the `schools.json` already on
  disk when it writes `dist/schools.json`. At page-build time only the kunta can be re-derived — the
  kunta rings are already loaded for `dist/geo/kunnat_lookup.json`, the finer rings are not — so the
  **postal code and osa-alue of a moved school are cleared rather than guessed**, and the kunta
  benchmark is recomputed through `build_schools.kunta_benchmarks()`, the one definition of that mean.
  Everything else about the school layer is exactly what the last real fetch produced.
- **W1** — **Registry text and colour are refreshed from `config/indicators.json` at page build
  time.** `data/processed/makro.json` embeds a copy of the registry taken when the figures were last
  fetched, so a one-character fix in config would otherwise have waited for the next national fetch to
  reach a reader — and tonight's two fixes (`Transport projects within 1,2 km`, and the Housing-stock
  hue) are both presentation. `build_dashboard.py` now refreshes **only** `label · short · unit ·
  desc · note · warn · hue · group · chip`, only for keys the built registry already has, and prints
  every field it touched. Nothing that decides a *value* — table ids, `vars`, `calc`, `select`,
  sources — is read from config here, so the figures on the page stay the ones the fetch produced.
  Tonight that is five fields, and the build says which five.
- **W1** — **RAMP6: the Housing-stock blue becomes a plum, `[138, 58, 122]`.** `renters` and `flats`
  were `[40, 84, 128]` and the Climate family ramp is `[47, 78, 140]` — the same hue to within 6°, on
  maps a reader switches between. Every neighbouring band of the wheel is already spoken for
  (observed green 160–170°, Climate blue 220°, projection purple 252°, Safety gold 30°, Construction
  brown 25°, Market brick 11°), and the one real gap is at ~310°. `dw_pre1980` was the darker of the
  two blues and keeps that relationship at `[120, 44, 106]`. Contrast, computed on the shipped ramp:
  darkest class `rgb(99,42,88)` is **10,5:1** against white label text, **6,3:1** against the no-data
  grey `#C4CBC4`, and **7,7:1** against its own lightest class — all above the 3:1 the v2.1 rule
  sets. The three Housing-stock indicators that are `[90, 60, 150]` (`avg_m2`, `m2_person`,
  `bld_m2_per_dwelling`) are **left alone and flagged instead**: that violet is within 6° of the
  projection family hue, which is the same fault one group over, and picking a second new hue
  unreviewed would have been a bigger change than the audit row asks for.
