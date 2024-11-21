.PHONY: clean install format lint test security build all

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -f .coverage
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

install:
	pip install -e ".[dev]"

format:
	black .
	isort .

lint:
	ruff check .

test:
	pytest --cov=codegate --cov-report=term-missing

security:
	bandit -r src/

build: clean test
	python -m build

all: clean install format lint test security build
