# STAC Catalog Populator

![Latest Version](https://img.shields.io/badge/latest%20version-0.0.1-blue?logo=github)
![Commits Since Latest](https://img.shields.io/github/commits-since/crim-ca/stac-populator/0.0.1.svg?logo=github)

This repository contains a framework [STACpopulator](STACpopulator)
that can be used to implement concrete populators (see [implementations](STACpopulator/implementations))
for populating the STAC Catalog, Collections and Items from various dataset/catalog sources, and pushed using
STAC API on a server node.

## Framework

The framework is centered around a Python Abstract Base Class: `STACpopulatorBase` that implements all the logic
for populating a STAC catalog. This class provides abstract methods that should be overridden by implementations that
contain all the logic for constructing the STAC representation for an item in the collection that is to be processed.

## Implementations

Provided implementations of `STACpopulatorBase`:

- [CMIP6_UofT][CMIP6_UofT]

[CMIP6_UofT]: STACpopulator/implementations/CMIP6_UofT/add_CMIP6.py

## Testing

The provided [`docker-compose`](docker-compose.yml) configuration file can be used to launch a test STAC server.
For example, the [CMIP6_UofT][CMIP6_UofT] script can be run as:

```shell
python STACpopulator/implementations/CMIP6_UofT/add_CMIP6.py \
    "http://localhost:8880/stac/" \
    "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.html" \
    "STACpopulator/implementations/CMIP6_UofT/collection_config.yml"
```

*Note*:
In the script above, a sample THREDDS catalog URL is employed and not one relevant to the global scale CMIP6 data.
