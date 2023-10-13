IMP_DIR = STACpopulator/implementations
STAC_HOST = http://localhost:8880/stac

testcmip6:
	python $(IMP_DIR)/CMIP6-UofT/add_CMIP6.py $(STAC_HOST) https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.html $(IMP_DIR)/CMIP6-UofT/CMIP6.yml


starthost:
	docker compose up

stophost:
	docker compose down

del_docker_volume: stophost
	docker volume rm stac-populator_stac-db

resethost: del_docker_volume starthost
