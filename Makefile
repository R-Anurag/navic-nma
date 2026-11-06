PY ?= .venv/bin/python
export PYTHONPATH := src

test:
	$(PY) -m pytest -q

experiments:
	$(PY) experiments/run_matrix.py

figures:
	$(PY) experiments/figures.py

demo:
	$(PY) -m nma.demo

demo-html:
	$(PY) -m nma.demo --html demo/demo.html

all: test experiments figures demo-html

.PHONY: test experiments figures demo demo-html all
