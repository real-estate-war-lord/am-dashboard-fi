# AM Dashboard — Finland Edition · one command per pipeline step
# Targets grow as the phases land (docs/PLAN.md); every one of them is stdlib-only Python
# unless it says otherwise. `geo` is the single step that may want shapely/pyproj —
# everything else, including `build`, runs without them.
PY ?= python3

probe:      ## live endpoint probe of every batch-1 source → docs/PROBE_FI.md
	$(PY) scripts/probe_fi.py
validate:   ## check every table/variable/value code in config against the live StatFin metadata
	$(PY) scripts/validate_config.py && $(PY) scripts/check_source_links.py --quick --sample 2
verify:     ## recompute figures straight from the publisher and compare with the page
	$(PY) scripts/verify.py
links:      ## the full source-link sweep: every verify-at-source URL fetched (slow)
	$(PY) scripts/check_source_links.py
geo:        ## vendor kunta / maakunta / postinumero / osa-alue polygons (Tilastokeskus + Paavo + HSY)
	$(PY) scripts/fetch_geo_fi.py && $(PY) scripts/fetch_paavo.py
schools:    ## Tilastokeskus school register + YTL matriculation results -> the schools layer
	$(PY) scripts/build_schools.py
infra:      ## Väylävirasto project layers + the curated major projects -> the infra overlay
	$(PY) scripts/build_infra.py
services:   ## OSM + HSL GTFS + Palvelukartta -> services and public-building layers (needs requirements-services.txt)
	$(PY) scripts/fetch_services.py && $(PY) scripts/build_services.py
climate:    ## SYKE flood-hazard rasters + STUK radon -> data/processed/climate.json (needs requirements-geo.txt)
	$(PY) scripts/fetch_flood.py && $(PY) scripts/build_climate.py
addr:       ## pull every building address in Finland (Ryhti) and build the lazy lookup
	$(PY) scripts/fetch_addresses.py && $(PY) scripts/build_addr.py
fetch:      ## pull every StatFin table named in config/indicators.json, and the file sources
	$(PY) scripts/fetch_statfin.py && $(PY) scripts/import_kela.py && $(PY) scripts/import_verohallinto.py
build:      ## raw -> processed -> dist/index.html
	$(PY) scripts/build_makro.py && $(PY) scripts/build_osa.py && $(PY) scripts/build_dashboard.py
serve:      ## open the dashboard locally
	cd dist && $(PY) -m http.server 8080
test-js:    ## parser unit tests (node --test)
	node --test tests/*.test.js
test:       ## every unit test (python + js)
	$(PY) -m unittest discover -s tests -p 'test_*.py' && $(MAKE) test-js
fixture:    ## synthetic render check (never ship)
	$(PY) tests/make_fixture.py && $(PY) scripts/build_dashboard.py --data tests/fixture_makro.json --osa tests/fixture_osa.json --out dist/fixture.html
refresh: fetch build
.PHONY: probe validate verify links geo addr climate services infra schools fetch build serve fixture refresh test test-js
