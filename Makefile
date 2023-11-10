MAKEFILE_NAME := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
# Include custom config if it is available
-include Makefile.config
APP_ROOT    := $(abspath $(lastword $(MAKEFILE_NAME))/..)
APP_NAME    := STACpopulator
APP_VERSION ?= 0.2.0

DOCKER_COMPOSE_FILES := -f "$(APP_ROOT)/docker/docker-compose.yml"
DOCKER_TAG := ghcr.io/crim-ca/stac-populator:$(APP_VERSION)

IMP_DIR := $(APP_NAME)/implementations
STAC_HOST ?= http://localhost:8880/stac
# CATALOG = https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.html
CATALOG = https://daccs.cs.toronto.edu/twitcher/ows/proxy/thredds/catalog/datasets/CMIP6/catalog.html
# CATALOG = https://daccs.cs.toronto.edu/twitcher/ows/proxy/thredds/catalog/datasets/CMIP6/CMIP/NOAA-GFDL/catalog.html
# CATALOG = https://daccs.cs.toronto.edu/twitcher/ows/proxy/thredds/catalog/datasets/CMIP6/CMIP/AS-RCEC/catalog.html

## -- Testing targets -------------------------------------------------------------------------------------------- ##

setup-pyessv-archive:
	git clone "https://github.com/ES-DOC/pyessv-archive" ~/.esdoc/pyessv-archive

test-cmip6:
	python $(IMP_DIR)/CMIP6_UofT/add_CMIP6.py $(STAC_HOST) $(CATALOG)

del-cmip6:
	curl --location --request DELETE '$(STAC_HOST)/collections/CMIP6_UofT'
	@echo ""

docker-start:
	docker compose $(DOCKER_COMPOSE_FILES) up
starthost: docker-start

docker-stop:
	docker compose $(DOCKER_COMPOSE_FILES) down
stophost: docker-stop

docker-build:
	docker build "$(APP_ROOT)" -f "$(APP_ROOT)/docker/Dockerfile" -t "$(DOCKER_TAG)"

del_docker_volume: stophost
	docker volume rm stac-populator_stac-db

resethost: del_docker_volume starthost

install:
	pip install "$(APP_ROOT)"

install-dev:
	pip install "$(APP_ROOT)[dev]"

test-unit:
	pytest "$(APP_ROOT)"

test-cov:
	pytest "$(APP_ROOT)" --cov="$(APP_NAME)" --cov-report=term --cov-report=html

## -- Versioning targets -------------------------------------------------------------------------------------------- ##

# Bumpversion 'dry' config
# if 'dry' is specified as target, any bumpversion call using 'BUMP_XARGS' will not apply changes
BUMP_TOOL := bump-my-version
BUMP_XARGS ?= --verbose --allow-dirty
ifeq ($(filter dry, $(MAKECMDGOALS)), dry)
	BUMP_XARGS := $(BUMP_XARGS) --dry-run
endif
.PHONY: dry
dry: pyproject.toml		## run 'bump' target without applying changes (dry-run) [make VERSION=<x.y.z> bump dry]
	@-echo > /dev/null

.PHONY: bump
bump:  ## bump version using VERSION specified as user input [make VERSION=<x.y.z> bump]
	@-echo "Updating package version ..."
	@[ "${VERSION}" ] || ( echo ">> 'VERSION' is not set"; exit 1 )
	@-bash -c '$(CONDA_CMD) $(BUMP_TOOL) $(BUMP_XARGS) --new-version "${VERSION}" patch;'

.PHONY: version
version:	## display current version
	@-echo "$(APP_NAME) version: $(APP_VERSION)"
