PYTHON ?= python3
NPM ?= npm

.PHONY: setup masters build validate test specimens release clean

setup:
	$(PYTHON) -m pip install -r requirements.txt
	$(NPM) install
	$(NPM) exec playwright install chromium

masters:
	$(PYTHON) source/generate_signature_masters.py

build: masters
	$(PYTHON) source/build.py
	$(PYTHON) source/factsheet_data.py
	$(PYTHON) source/ligature_audit.py

validate:
	$(PYTHON) source/validate.py
	$(PYTHON) source/validate_geometry.py

test: validate
	$(NPM) run test:browser

specimens:
	$(PYTHON) source/specimens.py
	$(PYTHON) source/outline_proof.py
	$(PYTHON) source/signature_proof.py
	$(PYTHON) source/interpolation_diagnostics.py
	$(PYTHON) source/desktop_specimen.py
	$(NPM) run test:browser
	$(NPM) run test:factsheet
	$(NPM) run test:desktop

release: build test specimens
	$(PYTHON) source/package_release.py

clean:
	$(PYTHON) -c 'from pathlib import Path; import shutil; shutil.rmtree(Path("build"), ignore_errors=True)'
