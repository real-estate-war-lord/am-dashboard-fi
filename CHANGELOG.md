# Changelog

All notable changes to the Finland edition. Dates are the build date, not the data's.

## [v1.0] — 2026-09-24 (draft, unreleased)

The first complete edition: three map levels, 59 indicators, everything from open official
Finnish sources.

### Added

**Geography** — 308 kunnat (kuntajako 2026), 19 maakunnat, 3 018 postinumeroalueet (Paavo
`pno_tilasto_2026`) and 306 osa-alueet over Helsinki, Espoo, Vantaa and Kauniainen, all in
EPSG:4326, simplified with keep-shapes so no island and no hole is lost. The official
kunta → maakunta correspondence comes from Tilastokeskus's classification API, not from a
spatial guess.

**Demographics and income (Paavo, both levels, same definitions)** — population growth,
median income of inhabitants, mean household income, share aged 20–34, one-person
households, renter households, unemployment, tertiary education, dwellings in blocks of
flats, average dwelling size, floor area per person. Plus foreign-language speakers and the
monthly TEM unemployment rate per kunta, and housing-allowance households from Kela.

**Market** — old-flat price per m² and the sales count behind it (kerrostalo and rivitalo
separately, postal and kunta), free-market rent, ARA rent, rent change y/y and the
observation count, the discontinued postal-code rent series, unoccupied dwellings, total and
intermunicipal net migration, and dwellings completed / started / permitted per 1 000
dwellings. Yearly | Quarterly toggle on the publisher's own quarterly series.

**Taxes** — property tax on a permanent dwelling, on another dwelling, general (building),
general (land), an undeveloped building site, and the municipal income-tax rate.

**Safety** — reported penal-code offences, violence, property crime, criminal damage,
narcotics, dwelling burglary per 1 000 dwellings, and the y/y trend, with direction-aware
ranks and colours.

**Outlook** — Väestöennuste 2024: change 2026→2040 in per cent and in people, the five-year
change and rate, the 0–6, 7–15, 20–34 and 80+ bands, and the projected 20–34 share against
Finland's own. Observed solid, projected dashed, split at the last observed year. Helsingin
kaupunki's own projection by osa-alue is carried beside Tilastokeskus's for the city, with
the gap stated and never averaged.

**Osa-alue level** — nine indicators from Aluesarjat, area pages, and the breadcrumb
kunta → postinumero → osa-alue.

**Infrastructure** — a throttled, stamped StatFin PxWeb client; an Aluesarjat client; a
Verohallinto importer; a Kela importer; a calc engine that keeps suppression as null all the
way to the page; a live endpoint probe; and `scripts/verify.py`, which re-queries the
publishers and compares: **57 checks, 0 disagreements**.

### Notable decisions

- **Paavo is the backbone**, because it publishes the same definitions at kunta and postal
  level, so the two are directly comparable.
- **Lazy payloads.** The page carries the latest value of everything; history, detailed
  postal rings, monthly series and the osa-alue layer's geometry are fetched per kunta or on
  demand. `dist/index.html` is 2.4 MB with a hard 3 MB guard in the build.
- **° and ^** mark a value published for a coarser area than the row. A definition that
  differs between levels gets a different name, not the same name with a different meaning.

### Known gaps

No days-on-market or supply; no transaction-level prices; crime only at kunta level and
never quarterly; no comprehensive-school results; **no municipal construction data anywhere
in Finland** (maakunta only); postal-code rents frozen at 2025Q4; three incompatible
postal-code classification vintages; Paavo two years behind its release.

### Licence note

⚠ **Aluesarjat, the source of every osa-alue figure, allows non-commercial use only.** It is
not CC BY 4.0 like the rest of the dashboard. The restriction is labelled in the data, in
each osa-alue indicator's note and in the Sources view, and is an open item for the release
decision.

> **Corrected in v1.1 — this note was wrong.** Aluesarjat's own terms permit commercial use:
> "Tietoaineistoa voi käyttää sekä ei-kaupallisiin että kaupallisiin tarkoituksiin"
> (https://kaupunkitieto.hel.fi/fi/helsingin-tilastotietokannat/aluesarjat). The v1.0 text
> above is left standing because it is what v1.0 shipped; see the v1.1 entry.

### Not in this release

Test property, Analysis and Compare; climate risk; services; public buildings; infra
projects; schools; the buildings micro layer; energy certificates; zoning; the 1 km grid.
Their machinery is in `src/app.js`, dormant, for batch 2 (`docs/BUILD_PLAN_FI.md` §7).
National macro — Euribor, mortgage rates, bond yields, CPI, GDP, municipal finances — is out
of scope by decision, and the Danish market panel was removed rather than ported.
