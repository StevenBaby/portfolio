# Portfolio Docker workflow.
# Override values on the command line, for example:
#   make build IMAGE_TAG=v1
#   make run HOST_PORT=8080
#   make build CACHE=0

IMAGE_NAME ?= portfolio
IMAGE_TAG  ?= latest
FULL_IMAGE_NAME := $(IMAGE_NAME):$(IMAGE_TAG)
CONTAINER_NAME ?= portfolio
HOST_PORT ?= 5174
DOCKERFILE ?= Dockerfile
CACHE ?= 1

ifeq ($(CACHE),0)
NOCACHE_ARG := --no-cache
endif

.DEFAULT_GOAL := help
.PHONY: help build run restart logs status shell stop remove rm clean

help:
	@echo "Available targets:"
	@echo "  build    - Build $(FULL_IMAGE_NAME)"
	@echo "  run      - Run container at http://localhost:$(HOST_PORT)"
	@echo "  restart  - Recreate the container from the current image"
	@echo "  logs     - Follow container logs"
	@echo "  status   - Show container status"
	@echo "  shell    - Open a shell in the running container"
	@echo "  stop     - Stop the running container"
	@echo "  remove   - Force-remove the container (alias: rm)"
	@echo "  clean    - Remove the container and image"
	@echo ""
	@echo "IMAGE=$(FULL_IMAGE_NAME)  CONTAINER=$(CONTAINER_NAME)  HOST_PORT=$(HOST_PORT)"

build:
	@echo "Building $(FULL_IMAGE_NAME)..."
	docker build $(NOCACHE_ARG) \
		$(if $(HTTP_PROXY),--build-arg HTTP_PROXY=$(HTTP_PROXY)) \
		$(if $(HTTPS_PROXY),--build-arg HTTPS_PROXY=$(HTTPS_PROXY)) \
		$(if $(NO_PROXY),--build-arg NO_PROXY=$(NO_PROXY)) \
		-t $(FULL_IMAGE_NAME) -f $(DOCKERFILE) .

run:
	@echo "Running $(CONTAINER_NAME) at http://localhost:$(HOST_PORT)..."
	@docker rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true
	docker run -d \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		-p $(HOST_PORT):80 \
		-v $$(pwd)/trade:/app/trade:ro \
		$(FULL_IMAGE_NAME)

restart: run

logs:
	docker logs -f $(CONTAINER_NAME)

status:
	docker ps -a --filter name=^/$(CONTAINER_NAME)$$ \
		--format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

stop:
	-docker stop $(CONTAINER_NAME)

remove rm:
	-docker rm -f $(CONTAINER_NAME)

clean: remove
	-docker rmi $(FULL_IMAGE_NAME)
