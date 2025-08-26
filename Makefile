# SimTool Makefile

.PHONY: install install-dev test lint clean docs example help

help:
	@echo "SimTool Development Commands:"
	@echo "  install      - Install simtool"
	@echo "  install-dev  - Install in development mode with dev dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting and formatting"
	@echo "  clean        - Clean build artifacts"
	@echo "  example      - Run counter example"
	@echo "  help         - Show this help"

install:
	pip install .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	flake8 simtool/ --max-line-length=100
	black simtool/ --check

format:
	black simtool/

clean:
	rm -rf build/ dist/ *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

example: install
	@echo "Running counter example..."
	cd examples/counter && \
	simtool doctor && \
	simtool vlog rtl/counter.sv --top counter && \
	echo "Compilation successful! Now run: simtool sim counter --waves"

# Development shortcuts
dev-setup: install-dev
	@echo "Development environment ready!"

.DEFAULT_GOAL := help