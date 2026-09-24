# Data folders — one way, one producer

The pipeline flows one way, and **exactly one script writes each folder**. If you are
unsure where a number came from, walk the chain backwards: the page reads `dist/`, which is
assembled from `data/processed/`, which is computed from `data/raw/` + `data/geo/` +
`data/external/`, each of which records where it came from.

```
data/
├── raw/<source>/          untouched pulls, one file per table + a *.meta.json stamp
│                          producer: scripts/fetch_*.py          in git: only *.meta.json
├── geo/                   simplified GeoJSON the page draws
│                          producer: scripts/fetch_geo_fi.py, fetch_paavo.py   in git: yes
│   └── raw/               the unsimplified WFS downloads                      in git: no
├── external/              small file-sourced CSVs (Verohallinto, Kela)
│                          producer: scripts/import_*.py          in git: yes (CSV, not the source XLSX/PDF)
└── processed/             the JSON the page reads
                           producer: scripts/build_makro.py       in git: yes
dist/                      the assembled page
                           producer: scripts/build_dashboard.py   in git: no (built by CI)
```

## The rules

1. **Nothing is edited by hand in `data/processed/`.** It is a build output. Fix the
   config or the build script and rebuild.
2. **Every raw pull carries a stamp.** `scripts/statfin.py` writes `<file>.meta.json` next
   to every pull with the table name, the request URL, the exact query, the publisher's own
   `updated` timestamp, the fetch date and the licence. The stamps are committed even though
   the pulls are not, so a committed figure can always be traced to a dated request.
3. **Raw pulls are never committed.** They are re-downloadable and large. `.gitignore`
   keeps `data/raw/**` out and lets `*.meta.json` through.
4. **Source files stay out, extracts go in.** A Verohallinto XLSX or a Kela export is
   downloaded to `data/external/raw/` (ignored) and the parsed CSV is committed, so a
   reviewer can diff the numbers without the repo carrying binaries.
5. **No processed or dist file over 3 MB.** Anything bigger is split per kunta and loaded
   on demand by the page (`dist/micro/<kunta>.json`, `dist/services/<kunta>.json`).
6. **Suppressed is not zero.** A cell the publisher suppressed is `null` through the whole
   chain and renders as `–`. An area we do not cover reads "Not covered yet".
7. **Codes are strings.** Kunta `"091"`, postinumero `"00100"`. Nothing casts them to int,
   anywhere, ever.
8. **Vintages are pinned.** See `docs/GEO.md`: each table's area classification carries its
   own year, and two vintages are never joined without a documented crosswalk.
