# v2.2 — what each phase shipped

Branch `v2.2-ui`, six sequential unattended phases (W1…W6): cleanup, readable maps and charts, a better
Test property first screen, a presentation mode and the Danish SHOULD list. Live today: FI v2.1
(tag `v2.1`, branch `main`). **Never pushed, merged or tagged by a phase** — `./overnight.sh release`
does that in the morning.

Read alongside `docs/v2_1/PARITY_AUDIT.md` (the gap list — phases cite its row ids) and
`docs/v2_2/DECISIONS.md` (every choice taken in the dark).

---

## W1 — cleanup: the lost v2.1 V7 fixes and the small data items ☑

Gate: `./overnight.sh gate W1` green — build ✓, 70 node tests ✓, the full ui suite up to W1 ✓
(6 new checks), budgets `src/app.js` 453 KB / 460, `src/style.css` 144 KB / 165. The python unit
suite is green.

**Built**

1. **The build line says which release this is** (`src/app.js`). One `APP_VERSION = "2.2"`, read by
   the sidebar footer and by nothing else; it had said `v2.0` since v2.0 because the string lived in
   the footer's markup. Check `W1-build-line-version` asserts the line and the constant agree and
   that no second version literal exists in `src/app.js`.
2. **A project sheet knows the areas it serves** (`vProject`, `infraPopup`, `vPipeline`,
   `exportPipelineCsv`). `properties.kunnat` is a Danish field that no Finnish project carries, so
   *Areas served* was empty on all 169 sheets, the Municipalities column of Data › Projects was empty
   on every row, and a map popup never named a municipality. All four now read `dist/infra_index.json`
   — inverted once into `id → {kunta codes}` and cached — and 157 of the 169 projects name at least
   one kunta. Postal codes and osa-alueet were already read from the same index on the sheet; the
   projects CSV gains a `postinumerot` column so the export says what the sheet says.
   Check `W1-project-areas-served`.
3. **A project with no published alignment says "Not covered yet"** instead of drawing a blank map and
   an empty card, and the mini map opens on **Finland**: it was created at `[56, 10.5]`, which is
   Jutland. `FI_CENTER` is derived from `FI_BOX` so the two cannot drift.
   Check `W1-project-map-in-finland`.
4. **The school sheet explains Finland without reaching for Denmark.** "unlike Denmark's socioeconomic
   reference, there is no Finnish equivalent to show here" is now a statement about Finland: no entry
   average, no catchment, no background figure per lukio, so the two rows above the sentence are the
   only comparison there is.
5. **A year never gets a thousands separator** — `1 987 — 2 000` in the buildings legend. One
   `fmtYear()`, wired into `FMT`, `FMT_TIGHT` and the building popup's *Completed* row, and
   `MICRO_INDS.year` moved from `fmt: "int"` to `fmt: "year"`.
   Check `W1-years-have-no-separator`.
6. **The chart's title and sub-title stay on the canvas**, on screen and in the downloaded PNG. A
   reused 2-D canvas measures the real font, the line is cut on a word with an ellipsis, and the full
   string stays in the element's `<title>`. The line chart's own copy of the title block is gone —
   `chTitleBlock()` draws all three chart kinds now, so bar, distribution and line cannot diverge.
   Check `W1-chart-subtitle-fits`.
7. **README's screenshot is build output.** `tests/ui_v2.spec.py` writes `docs/screenshot.png` from
   the map-at-1440 shot it already takes, so it cannot go a release stale again.
8. **`Transport projects within 1.2 km` → `1,2 km`** in `config/indicators.json` (label and short),
   the morning task v2.1's V6 logged. It reaches the page because `build_dashboard.py` now refreshes
   the registry's **text and colour** fields from config at page build time — see DECISIONS W1 for
   exactly which nine fields, and why no field that decides a value is among them.
9. **`Oulun normaalikoulu` is in Oulu.** `data/external/overrides/schools.csv` is the one place a
   school's coordinate may be corrected; `scripts/build_schools.py` applies it before placing the
   school, and `scripts/build_dashboard.py` applies the same file to the `schools.json` on disk so the
   fix lands without a register re-fetch. The replacement point is not typed in from an address: it is
   OpenStreetMap's own `amenity=school` "Oulun normaalikoulun lukio" out of this dashboard's
   public-buildings layer. The school sheet prints where a replaced coordinate came from.
   Check `W1-school-coord-override`.
10. **RAMP6** — the Housing-stock blue (`renters`, `flats`, `dw_pre1980`) becomes a plum,
    `[138, 58, 122]` / `[120, 44, 106]`. Contrast computed and logged in DECISIONS W1: 10,5:1 against
    white label text, 6,3:1 against the no-data grey, 7,7:1 across its own ramp.

**Left for a later phase (found, not fixed)**

- `avg_m2`, `m2_person` and `bld_m2_per_dwelling` are `hue: [90, 60, 150]`, within 6° of the
  projection family hue `[91, 74, 156]` — the same fault RAMP6 names, one group over. Flagged rather
  than fixed: a second unreviewed hue is more change than the audit row asks for.
- `school_grade_avg` / `schools_n` are read by `schoolLine()` and by the school-list header, and no
  build writes them — the per-area school aggregate never renders. It is a pipeline gap, not a UI one.
- A school moved by an override keeps `postinumero` and `osa_alue` empty until the next real
  `build_schools.py` run, because the finer rings are not loaded at page build time. Empty, never
  wrong.
