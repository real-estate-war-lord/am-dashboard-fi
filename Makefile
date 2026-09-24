# AM Dashboard — Finland Edition · one command per pipeline step
# Targets grow as the phases land (docs/PLAN.md); every one of them is stdlib-only Python
# unless it says otherwise. `geo` is the single step that may want shapely/pyproj —
# everything else, including `build`, runs without them.
PY ?= python3

probe:      ## live endpoint probe of every batch-1 source → docs/PROBE_FI.md
	$(PY) scripts/probe_fi.py
validate:   ## check every table/variable/value code in config against the live StatFin metadata
	$(PY) scripts/validate_config.py && $(PY) scripts/check_source_links.py --quick --sample 2
links:      ## the full source-link sweep: every verify-at-source URL fetched (slow)
	$(PY) scripts/check_source_links.py
geo:        ## vendor kunta / maakunta / postinumero / osa-alue polygons (Tilastokeskus + Paavo + HSY)
	$(PY) scripts/fetch_geo_fi.py && $(PY) scripts/fetch_paavo.py
fetch:      ## pull every StatFin table named in config/indicators.json to data/raw
	$(PY) scripts/fetch_statfin.py
build:      ## raw -> processed -> dist/index.html
	$(PY) scripts/build_dashboard.py
serve:      ## open the dashboard locally
	cd dist && $(PY) -m http.server 8080
test-js:    ## parser unit tests (node --test)
	node --test tests/*.test.js
test:       ## every unit test (python + js)
	$(PY) -m unittest discover -s tests -p 'test_*.py' && $(MAKE) test-js
fixture:    ## synthetic render check (never ship)
	$(PY) tests/make_fixture.py && $(PY) scripts/build_dashboard.py --data tests/fixture_makro.json --osa tests/fixture_osa.json --out dist/fixture.html
refresh: fetch build
.PHONY: probe validate links geo fetch build serve fixture refresh test test-js
