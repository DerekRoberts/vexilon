.PHONY: dev down test test-all build

# Auto-detect if podman or docker is installed
COMPOSE := $(shell command -v podman-compose 2> /dev/null || echo docker compose)
ifeq ($(COMPOSE),docker compose)
	COMPOSE := docker compose
else
	COMPOSE := podman compose
endif

dev:
	$(COMPOSE) -f app/compose.yml up --build dev

down:
	$(COMPOSE) -f app/compose.yml down -v

build:
	$(COMPOSE) -f app/compose.yml build

test:
	cd app && uv run pytest ../tests/deploy_integrity/ tests/test_rag_stream.py -v

test-all:
	$(COMPOSE) -f app/compose.yml up --build test-everything
