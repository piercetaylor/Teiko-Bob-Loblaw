PYTHON ?= python3

.PHONY: setup pipeline dashboard test

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) -m cellcounts.report

dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.headless true

test:
	$(PYTHON) -m pytest test/ -q
