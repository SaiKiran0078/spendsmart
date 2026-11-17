.PHONY: install run test lint format seed

install:
	pip install -r requirements-dev.txt

run:
	uvicorn app.main:app --reload

test:
	pytest --cov=app --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

seed:
	python -m scripts.seed_demo
