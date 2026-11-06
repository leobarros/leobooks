SHELL := /bin/bash

COMPOSE ?= docker compose
SERVICE ?= leobooks
HOST_PORT ?= 5059
HEALTH_URL ?= http://127.0.0.1:$(HOST_PORT)/healthz
REGISTRY ?= docker.io
IMAGE_NAME ?= nickolback/leobooks
IMAGE_TAG ?= latest
IMAGE ?= $(IMAGE_NAME):$(IMAGE_TAG)
PUSH_TAG := $(if $(filter push,$(MAKECMDGOALS)),$(word 2,$(MAKECMDGOALS)),)

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.DEFAULT_GOAL := help
.PHONY: help setup setup-dev local run test verify \
        pull docker-pull docker-build up docker-up up-build docker-up-build \
        login push \
        down docker-down stop docker-stop restart docker-restart \
        ps docker-ps logs docker-logs shell health image version clean

help:
	@echo "LeoBooks — comandos"
	@echo ""
	@echo "  make local              sobe o projeto local com ./run.sh (5057)"
	@echo "  make test               roda a suíte pytest"
	@echo "  make verify             pytest + build e healthcheck do Docker"
	@echo ""
	@echo "  make pull               baixa a imagem mais recente do Docker Hub"
	@echo "  make up                 pull + docker compose up -d + healthcheck"
	@echo "  make up-build           build da imagem local + up + healthcheck"
	@echo "  make login              faz login no registry"
	@echo "  make push               build + push da imagem latest"
	@echo "  make push v1            build + push da imagem v1"
	@echo "  make down               para o Compose (preserva o volume)"
	@echo "  make restart            reinicia o serviço"
	@echo "  make logs               acompanha os logs"
	@echo "  make ps                 mostra o status do container"
	@echo "  make shell              abre um shell no container"
	@echo "  make health             verifica http://127.0.0.1:5059/healthz"
	@echo "  make image              mostra a imagem configurada"
	@echo "  make version            mostra VERSION"
	@echo "  make clean              limpa caches Python (não toca em dados)"
	@echo ""
	@echo "Variáveis: COMPOSE, SERVICE, HOST_PORT, REGISTRY, IMAGE_NAME, IMAGE_TAG"

setup: $(PYTHON)
	@echo "Ambiente local pronto."

setup-dev: $(PYTHON)
	$(PIP) install -q -r requirements-dev.txt
	@echo "Dependências de desenvolvimento prontas."

$(PYTHON):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

local: $(PYTHON)
	@echo "LeoBooks local: http://127.0.0.1:5057"
	./run.sh

run: local

test: setup-dev
	$(PYTHON) -m pytest -q

verify: test docker-up-build

pull: docker-pull

docker-pull:
	$(COMPOSE) pull $(SERVICE)

docker-build:
	$(COMPOSE) build

up: docker-up

docker-up: docker-pull
	$(COMPOSE) up -d --no-build
	@$(MAKE) --no-print-directory health

up-build: docker-up-build

docker-up-build: docker-build
	$(COMPOSE) up -d --no-build
	@$(MAKE) --no-print-directory health

login:
	docker login $(REGISTRY)

push:
	@tag="$(if $(PUSH_TAG),$(PUSH_TAG),latest)"; \
	echo "Building $(IMAGE_NAME):$$tag"; \
	LEOBOOKS_IMAGE_TAG="$$tag" $(COMPOSE) build; \
	docker push "$(IMAGE_NAME):$$tag"

down: docker-down

docker-down:
	$(COMPOSE) down

stop: docker-stop

docker-stop:
	$(COMPOSE) stop $(SERVICE)

restart: docker-restart

docker-restart:
	$(COMPOSE) restart $(SERVICE)
	@$(MAKE) --no-print-directory health

ps: docker-ps

docker-ps:
	$(COMPOSE) ps

logs: docker-logs

docker-logs:
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

shell:
	$(COMPOSE) exec $(SERVICE) sh

health:
	@ok=0; \
	for i in $$(seq 1 20); do \
	  if curl -fsS "$(HEALTH_URL)" >/dev/null 2>&1; then ok=1; break; fi; \
	  sleep 2; \
	done; \
	if [ $$ok -eq 1 ]; then \
	  echo "healthy: $(HEALTH_URL)"; \
	else \
	  echo "healthcheck falhou: $(HEALTH_URL)"; \
	  $(COMPOSE) ps; \
	  exit 1; \
	fi

image:
	@echo "$(IMAGE)"

version:
	@cat VERSION

clean:
	rm -rf .pytest_cache __pycache__ tests/__pycache__ utils/__pycache__
	find . -name '*.pyc' -not -path './.venv/*' -delete
	@echo "Caches removidos; dados preservados."

# `make push v1` treats v1 as a second goal; it is consumed by the push recipe.
ifneq ($(PUSH_TAG),)
$(PUSH_TAG):
	@:
endif
