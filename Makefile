.PHONY: install test lint format-check typecheck build verify-live api web

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install --require-hashes -r requirements.lock
	.venv/bin/python -m pip install --no-deps -e .
	npm ci

test:
	.venv/bin/pytest -m "not live"

lint:
	.venv/bin/ruff check .
	npm run lint

format-check:
	.venv/bin/ruff format --check .

typecheck:
	npm run typecheck

build:
	npm run build

verify-live:
	.venv/bin/sessionzero-verify-bitget --interval 1H --limit 5

api:
	.venv/bin/uvicorn sessionzero_api.main:app --host 127.0.0.1 --port 8000

web:
	npm run dev:web

