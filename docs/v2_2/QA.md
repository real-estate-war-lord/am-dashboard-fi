# v2.2 — QA, the morning after

The final pass of W6: the gate green, then the shots regenerated (`docs/ui_v2/*.png`, 58 files) and
**looked at** rather than only counted — every one of the 29 routes at **1440 × 900**, and a wide
sample at **390 × 844**, present mode among them. **Nothing below blocks the release.** Four things the screenshots showed were fixed in W6
and are listed first; everything after that is known, deliberate or upstream, and each entry says
which it is and where the fix would go.

The checks are `tests/ui_v2.spec.py` (**162**, run up to a phase with `PHASE=W6`) and
`node --test tests/*.test.js` (**132**). `./overnight.sh gate W6` runs both, plus the build, the
python unit tests, the screenshots and the budgets.

---

## Fixed in W6, because the screenshots showed them

| | What it looked like | What it is now | Check |
|---|---|---|---|
| **A bar chart of two areas** | 640 units of canvas for 104 units of bars — ~300 px of white between the last bar and the source line, on screen and in the downloaded PNG. On `#charts?…&mode=bar` it also pushed the Schools panel below it off the first screen. | The canvas is as tall as its rows need (52 units a row, the old geometry from nine areas up). | `W6-bar-chart-fits-rows` |
| **A chart's source footer** | The source line and its note were one string on one line. W5's climate-pair note is 160 characters on its own, so the line ran past the right edge of the 1 200-unit canvas and was cut by the viewBox — the reason the median tick is off was unreadable in the PNG. | Two lines, each measured and clipped on a word like the title block above them (W1), each keeping the whole string in its `<title>`. The line chart's bottom band grew 16 units so its legend cannot reach the new line. | `W6-chart-footer-fits` |
| **Project labels on the map** | A label whose anchor was off the left edge was clipped by the container to a mid-word fragment — the map read `än parantamin` at its own edge. The 95-px edge rule was a guess about a width nobody knows before the label is in the document. | A label is placed only where the whole of it fits, and the overhang is then *measured* and the label anchored the other way if it still crosses an edge. Labels are re-placed on `moveend`, so panning one into view names it. | `W6-infra-labels-inside-map` |
| **Data › Sources** | The only anchors in the build with no class on them: the browser's blue and its underline, in a column of otherwise ink-coloured titles. | The page's own ink, a hairline underline, still obviously a link. | `W6-source-links-styled` |

---

## Open — presentation

1. **The study-row chart is 80 px tall at 390 px, and its axis labels cannot be read.** The panel
   chart is a 900 × 240 SVG scaled to the card's width; at a phone's ~290 px that is a 0,32 scale,
   so an 11-unit tick label renders at 3,7 px. The lines, the series key and the clipped-scale note
   under it are HTML and stay legible, and **every figure the chart plots is also printed as text**
   above it (the value, the change, the rank, the last value per series), so nothing is lost — it is
   the *scale* that is unreadable. **The Charts view has the same fault one size up**: its SVG is
   1 200 × 640 and at 390 px even the title is a smudge — there the mitigation is the *Data* table
   directly under the chart, which lists every period and every value as text. Not fixed here
   because the honest fix is a second geometry under 1025 px (fewer ticks, a taller box, larger
   type in user units), which is a feature, not a QA tweak; stretching it with
   `preserveAspectRatio="none"` is ruled out by DECISIONS W4 ("a chart whose slopes lie"). The
   precedent to copy is already in the build: `schoolTrendSvg()` draws a small viewBox and stays
   legible at 390 px (`docs/ui_v2/charts_390.png`, the Schools panel at the bottom of the same
   page). Affects the area page, Test property and Charts.
2. **The macro map's legend can sit below the fold at 1440 × 900 with a pin card open.** W2 gives
   the map a 560 px floor; with the toolbar, the info strip, the area card and the pin card above
   it the map then ends ~80 px past the bottom of the window and the reader scrolls to see the key.
   Deliberate: a 440-px map is not a map of Finland. `docs/ui_v2/map_pin_1440.png`.
3. **Present mode does not re-fit the camera** (DECISIONS W4). Leaving the sidebar gives the map
   ~250 px more width; the map is told its container changed but keeps its centre and zoom, because
   moving the reader's view out from under them mid-sentence is worse than a little slack.
4. **Ten series on a Charts line chart** put the legend's fourth row close to the source footer.
   W6 bought 16 units where there is a footer note, which is the case that could collide; the plain
   ten-series case is as it was in v2.1 and still wants a proper row budget.
5. **Project labels crowd each other on a 390-px map.** W6 keeps every label inside the map, but the
   de-collision rule is a 78 × 20 px box tuned for a desktop map, and it does not know about the
   cluster badges at all — on a 330-px-wide map with the Infra layer on, two long names and a badge
   can still sit on top of each other (`docs/ui_v2/map_layers_390.png`). The fix is a width-aware
   spacing rule plus the badges in the same `placed` list; it is a change to how labels are chosen
   rather than where they are put, which is why W6 stopped at the edges. The *area* labels
   (`lfLabels()`) have the same edge case one layer down — a value label whose polygon centroid is
   within half a label of the map's edge is trimmed by the container on a phone
   (`docs/ui_v2/map_pin_390.png`, right edge) — and would take the same treatment W6 gave the
   project labels.
6. **The infra table on Test property scrolls sideways at 390 px** — it is a scroll container, not
   an overflow (`P9-no-overflow-390` covers the page itself), but the right-hand columns
   (`OPENING`, `DISTANCE`) are off screen until the reader drags. A card-per-row layout under
   1025 px is the fix, and it is a layout change rather than a QA one.

## Open — data and pipeline, not the interface

7. **`label_short` is cut at 28 characters, upstream, mid-word** — `Maantie 11746 Kilpilahden lä`,
   `Kantatie 51 (Länsiväylä) ja `, `HERI2 Kytömaa-Ainola, rakent`. W6 marks the cut with an ellipsis
   so the map no longer prints half a word as if it were a name, and the whole name is in the popup
   the label opens, but the cut itself belongs to the fetch script this branch may not touch.
8. **`school_grade_avg` / `schools_n` are read by `schoolLine()` and by the school-list header, and
   no build writes them** — the per-area school aggregate never renders (W1). A pipeline gap.
9. **No indicator in this edition carries a `breaks` entry**, so `chartBreaks()` draws nothing and
   the clipped-scale note can only ever say *"years not every series shown covers"* rather than
   naming a cause (W2). The moment the build writes one `breaks[].text` the note picks it up with
   no code change.
10. **A school moved by `data/external/overrides/schools.csv` keeps `postinumero` and `osa_alue`
    empty** until the next real `build_schools.py` run, because the finer rings are not loaded at
    page-build time (W1). Empty, never wrong.
11. **`avg_m2`, `m2_person` and `bld_m2_per_dwelling` are `hue: [90, 60, 150]`**, within 6° of the
    projection family's own hue — the same fault RAMP6 fixed one group over (W1). Flagged rather
    than fixed: a second unreviewed hue is more than the audit row asks for.

## Open — known limits carried forward from W3 and W5

12. **`tileStats()` still mixes levels across a series.** The current value resolves through
    osa-alue → postal code → kunta, but each earlier year resolves independently, so a sparkline
    could in principle change level mid-line. No indicator in this edition does it; the honest fix
    is to pin the series to the level the current value came from.
13. **An area page's osa-alue still falls straight to its kunta.** Only a *pin* has one postal code
    to fall to; a district overlaps several, and a range across them is not the figure (W3).
14. **The pins are only offered on the chip row.** An osa-alue page silently shows only the pins
    that level publishes, so the row can be shorter than the store and never says so (W5).
15. **`Columns ▾` is on Data › Areas only** — the area page's *All indicators* table and the
    property's *Area profile* have the same width and the same group structure (W5).
16. **The sparkline column is on the sub-areas table only.** `tileSpark()`, `schoolTrendSvg()` and
    `W5_CORE.sparkSegments` draw the same kind of thing three ways; none of them is wrong, they are
    simply not one function yet (W5).
17. **Print is asserted by Playwright's media emulation, not by a rendered PDF** (W4). The rules
    apply; the pagination is not proved by a test. This pass looked at it by hand instead.

## Budgets — where v2.2 leaves the next release

| | End of v2.2 | Ceiling | Free |
|---|---|---|---|
| `src/app.js` | 463 573 B | 471 040 B | **7,3 KB** |
| `src/style.css` | 165 118 B | 168 960 B | **3,8 KB** |
| `dist/index.html` | 3 285 650 B | 3 300 000 B | **14,0 KB** |

The page is the tight one. v2.2 added ~60 KB of source (six new files and the CSS) and **no data**;
W3's suggestion still stands as the honest next step before anything substantial is added: strip
comments from the *inlined* copy of the JavaScript while the repo keeps them, rather than deleting
the comments that are where every decision of four releases is written down. `src/style.css` is
next-tightest; the print block and the present block share enough selectors to merge if a phase
needs the room.

## What this pass could not check

- **Live basemap tiles.** The harness answers every off-machine request itself, so every map in
  `docs/ui_v2/` is drawn on the paper colour with no OpenStreetMap underneath, and the study-row
  PNG deliberately exercises its `· basemap omitted` path (DECISIONS W4). Contrast against real
  tiles is a thing to look at once on the published page.
- **A real printer.** A4 landscape is asserted under media emulation and was read on screen.
- **A screen reader.** The live region, the roles and the tab order are asserted structurally
  (`V6-a11y-sweep`, `V6-keyboard-popovers`, `W5-drill-announced`); nobody listened to it.
