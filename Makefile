PY ?= .venv/bin/python

setup:            ## create .venv and install everything
	python3 -m venv .venv
	$(PY) -m pip install -q -e '.[dev]'

platform:         ## start the food-delivery platform API on :8710
	$(PY) -m uvicorn services.app:app --port 8710

test:             ## run the test suite (no API key needed)
	$(PY) -m pytest -q

.PHONY: setup platform test
