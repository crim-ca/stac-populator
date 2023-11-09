IMP_DIR = STACpopulator/implementations
STAC_HOST = http://localhost:8880/stac
# CATALOG = https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.html
CATALOG = https://daccs.cs.toronto.edu/twitcher/ows/proxy/thredds/catalog/datasets/CMIP6/catalog.html
# CATALOG = https://daccs.cs.toronto.edu/twitcher/ows/proxy/thredds/catalog/datasets/CMIP6/CMIP/NOAA-GFDL/catalog.html
# CATALOG = https://daccs.cs.toronto.edu/twitcher/ows/proxy/thredds/catalog/datasets/CMIP6/CMIP/AS-RCEC/catalog.html

testcmip6:
	python $(IMP_DIR)/CMIP6_UofT/add_CMIP6.py $(STAC_HOST) $(CATALOG)

delcmip6:
	curl --location --request DELETE '$(STAC_HOST)/collections/CMIP6_UofT'
	@echo ""

starthost:
	docker compose up

stophost:
	docker compose down

del_docker_volume: stophost
	docker volume rm stac-populator_stac-db

resethost: del_docker_volume starthost
