# Convenience shortcuts. On Windows, run these from Git Bash or WSL.
.PHONY: help install run test seed lint clean

help:
	@echo "make install  - create backend/.venv and install dev dependencies"
	@echo "make run      - start the API on http://127.0.0.1:8000"
	@echo "make test     - run the test suite"
	@echo "make seed     - reset and load demo data"
	@echo "make lint     - run ruff"
	@echo "make clean    - remove caches and the local database"

install:
	cd backend && python -m venv .venv && \
		.venv/bin/python -m pip install --upgrade pip && \
		.venv/bin/python -m pip install -r requirements-dev.txt

run:
	cd backend && uvicorn main:app --reload --port 8000

test:
	cd backend && python -m pytest

seed:
	cd backend && python seed.py --reset

lint:
	ruff check backend

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf backend/.pytest_cache
	rm -f backend/chainguard.db
