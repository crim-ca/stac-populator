MAKEFILE_NAME := $(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
# Include custom config if it is available
-include Makefile.config
APP_ROOT    := $(abspath $(lastword $(MAKEFILE_NAME))/..)
APP_NAME    := $(shell basename $(APP_ROOT))
APP_VERSION ?= 0.1.0


IMP_DIR := STACpopulator/implementations
STAC_HOST ?= http://localhost:8880/stac

## -- Testing targets -------------------------------------------------------------------------------------------- ##

test-cmip6:
	python $(IMP_DIR)/CMIP6_UofT/add_CMIP6.py $(STAC_HOST) https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.html

del-cmip6:
	curl --location --request DELETE '$(STAC_HOST)/collections/CMIP6_UofT'
	@echo ""

docker-start:
	docker compose up
starthost: docker-start

docker-stop:
	docker compose down
stophost: docker-stop

del_docker_volume: stophost
	docker volume rm stac-populator_stac-db

resethost: del_docker_volume starthost

install:
	pip install "$(APP_ROOT)"

install-dev:
	pip install "$(APP_ROOT)[dev]"

test-unit:
	pytest "$(APP_ROOT)"

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
