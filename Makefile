# Do not remove this block. It is used by the 'help' rule when
# constructing the help output.
# help: Anomaly Detector Makefile help
# help:

SHELL := /bin/bash

.PHONY: help
# help: help				- Please use "make <target>" where <target> is one of
help:
	@grep "^# help\:" Makefile | sed 's/\# help\: //' | sed 's/\# help\://'

.PHONY: e
# help: e				- copy env
e:
	@cp env.example .env

.PHONY: b
# help: b				- build containers with Ollama
b:
	@COMPOSE_BAKE=true BUILDKIT_PROGRESS=plain docker compose -f docker-compose.yml \
	    -f docker-compose-cpu.yml up --build -d

.PHONY: fr
# help: fr				- pip freeze
fr:
	@pip freeze | grep -v 'wheel\|setuptools' > containers/requirements.txt

.PHONY: hc
# help: hc				- from ollama host models to container
hc:
	@sudo rsync -a --owner --group /usr/share/ollama/.ollama/ /opt/.anomaly_models/
