# STAC Catalog Populator

Populate STAC catalog with sample collection items via [CEDA STAC Generator](https://github.com/cedadev/stac-generator), employed in sample 
[CMIP Dataset Ingestion Workflows](https://github.com/cedadev/stac-generator-example/tree/master/conf).


**Sample call via Docker image**

```
docker run -e STAC_HOST=https://stac-dev.crim.ca/stac/ -e STAC_ASSET_GENERATOR_TIMEOUT=300 stac-populator
```
