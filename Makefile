PYTHON ?= python3
NPM ?= npm

.PHONY: setup build validate test specimens release clean

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(NPM) install
	$(NPM) exec playwright install chromium

build:
	$(PYTHON) source/build.py
	$(PYTHON) source/factsheet_data.py
	$(PYTHON) source/ligature_audit.py

validate:
	$(PYTHON) source/validate.py

test: validate
	$(NPM) run test:browser

specimens:
	$(PYTHON) source/specimens.py
	$(PYTHON) source/outline_proof.py
	$(PYTHON) source/desktop_specimen.py
	$(NPM) run test:browser
	$(NPM) run test:factsheet
	$(NPM) run test:desktop

release: build test specimens
	$(PYTHON) source/package_release.py

clean:
	$(PYTHON) -c 'from pathlib import Path; import shutil; shutil.rmtree(Path("build"), ignore_errors=True)'
