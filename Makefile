PYTHON ?= .venv/bin/python
.PHONY: install ingest run test check up down
install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.lock
	.venv/bin/pip install --no-deps -e .
ingest:
	$(PYTHON) -m enterprise.rag
run:
	$(PYTHON) scripts/dev.py
test:
	$(PYTHON) -m pytest --cov=enterprise --cov-report=term-missing --cov-report=json:docs/evidence/coverage.json --junitxml=docs/evidence/tests.xml
check:
	.venv/bin/ruff check src tests scripts
	.venv/bin/ruff format --check src tests scripts
	.venv/bin/mypy src/enterprise
up:
	docker compose up --build -d --wait
down:
	docker compose down
