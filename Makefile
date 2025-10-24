.PHONY: setup lint test clean run-all help

help:
	@echo "Available targets:"
	@echo "  setup       - Install Python dependencies"
	@echo "  lint        - Run code linting"
	@echo "  test        - Run unit tests"
	@echo "  clean       - Remove build artifacts"
	@echo "  run-all     - Run the complete pipeline"

setup:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .

lint:
	black --check src/ tests/ synthetic/
	flake8 src/ tests/ synthetic/ --max-line-length=120
	mypy src/ --ignore-missing-imports

test:
	pytest tests/ -v --cov=src --cov-report=html

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

run-all:
	./scripts/run_all.sh
