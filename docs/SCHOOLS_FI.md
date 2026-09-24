# Schools — what Finland publishes, and what it does not

## The headline, first

**Finland publishes no comprehensive-school results.** Not suppressed, not behind a licence,
not too expensive to buy: there is no national peruskoulu exam whose results are published per
school, because Finland does not run one for publication. **2 167 of the 2 501 schools** in
this layer are therefore a point on a map with a name, a type and a location, and the UI says
exactly that rather than showing an empty column that would read as a bad result.

The only school results that exist are the **lukio matriculation figures**.

## 1. School points — Tilastokeskus

| | |
|---|---|
| WFS | `https://geo.stat.fi/geoserver/oppilaitokset/wfs` |
| Layer | `oppilaitokset:oppilaitokset` |
| Schools | **2 501**, register year 2025 |
| Coordinates | **published** — nothing here is geocoded |
| Licence | **CC BY 4.0** — "Lähde: Tilastokeskus" |

| Type | Count |
|---|---:|
| Peruskoulut | 2 059 |
| Lukiot | 334 |
| Peruskouluasteen erityiskoulut | 62 |
| Perus- ja lukioasteen koulut | 46 |

The register publishes **no municipality code**, so each school is placed in its kunta, postal
area and osa-alue by point-in-polygon on this dashboard's own rings — the same lookup the
test-property pin uses. 2 498 of 2 501 land in a kunta; the 3 that do not are recorded as such.

## 2. Matriculation results — YTL

YTL's own statistics pages publish national aggregates as PDFs. It **also** publishes an open,
unauthenticated file per exam session:

    https://tiedostot.ylioppilastutkinto.fi/ext/data/FT<year><K|S>D4001.csv

**one row per candidate**, carrying the school number, the school name, and that candidate's
grade in each subject on YTL's own 0–7 scale, plus `yht`, the total grade points. Nine sessions
answer (2022K–2026K); 2026S is not published yet and is skipped rather than guessed at.

| Session | Candidates | Schools kept | Suppressed |
|---|---:|---:|---:|
| 2026K | 27 085 | 352 | 35 |
| 2025K | 26 392 | 354 | 35 |
| 2025S | 5 443 | 143 | 178 |

School-level figures are the mean over YTL's own published rows — plain arithmetic on published
cells, which is what this dashboard is allowed to do.

### Suppression

The file is **candidate-level**, so aggregating it is arithmetic on published rows but a mean
over three candidates describes three people. Therefore:

- a school session with fewer than **10 candidates** is suppressed;
- a **subject** fewer than 10 of that school's candidates sat is suppressed;
- **YTL's own `**` marker is read as suppressed too.**

A suppressed figure is **null, never zero**, and the UI's dash says so on hover. The autumn
session (S) is roughly a fifth the size of the spring one, so most schools are suppressed in it
— that is the register being honest, not a gap.

### The join, and why it is only an exact one

**The two publishers share no key.** Tilastokeskus numbers a school with a five-digit `tunn`
(`08888`); YTL numbers it with its own four-digit `koulun_nro` (`1488`). The systems are
unrelated, and zero-padding one into the other matches **nothing at all** — 0 of 387.

What they share is the school's **name**. Once case, punctuation and doubled spaces are
normalised, **336 of YTL's 387 names are exactly equal** to a register name.

So the join is **exact normalised-name equality, against upper-secondary schools only, and
nothing fuzzier**. A near match would attach one school's results to another school, and that
is precisely the kind of error nothing downstream would ever reveal.

**338 of 380 lukios are joined.** The 46 YTL schools left unjoined are adult lines
(*aikuislinja*, part of a parent lukio), schools abroad (Aurinkorannikon suomalainen lukio, in
Spain, is not in the Finnish register) and renamed schools. They are **listed in the payload**
under `join.unjoined_ytl_schools` and carry no result — rather than someone else's.

## 3. What the figure does and does not mean

`yht` is the **sum** of a candidate's grade points across the exams they sat. So:

- **a school whose candidates sit more exams scores higher for that reason alone**;
- **it tracks intake at least as much as teaching**;
- and unlike Denmark's socioeconomic reference, **Finland publishes no measure of intake** to
  set against it. There is nothing to show in that column, so the column is not there.

Every place the figure appears says this. It is a comparison of published figures, not a
ranking of schools.

## 4. Where it appears

| Where | What |
|---|---|
| Public buildings overlay, Education only | lukio markers coloured by matriculation points |
| School popup | points, the kunta mean and the Finland mean, side by side |
| School datasheet `#school/<tunn>` | every published session, every subject, the two benchmarks |
| Area school list `#schoollist/<level>:<code>` | the area's schools, sorted by points |
| Charts | a candidate-weighted municipal trend against Finland |

## 5. How to rebuild

    python3 -m pip install -r requirements-services.txt
    make schools     # scripts/build_schools.py

`data/processed/schools.json` is committed, so `make build` needs neither shapely nor a network.
