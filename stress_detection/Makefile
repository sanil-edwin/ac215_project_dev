.PHONY: help build run test format lint

help:
	@echo "make build    - build Docker image"
	@echo "make run      - run API on :8000"
	@echo "make test     - run pytest"
	@echo "make format   - run black + isort"
	@echo "make lint     - run ruff"

IMAGE?=agriguard:latest

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm -p 8000:8000 $(IMAGE)

test:
	pytest -q

format:
	black agriguard tests
	isort agriguard tests

lint:
	ruff check agriguard tests
