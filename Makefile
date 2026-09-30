.PHONY: setup build run test evaluate
setup:
	uv venv .venv
	uv pip install --python .venv/bin/python -r requirements.lock.txt
	.venv/bin/python scripts/init_env.py
	npm --prefix frontend ci
build:
	npm --prefix frontend run build
run:
	.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
test:
	.venv/bin/python -m pytest -q
evaluate:
	.venv/bin/python scripts/evaluate.py
