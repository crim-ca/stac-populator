# STAC Catalog Populator


This repository contains a framework [STACpopulator](STACpopulator) that can be used to implement concrete populators (see [implementations](implementations)) for populating the STAC catalog on a DACCS node.

## Framework

The framwork is centered around a Python Abstract Base Class: `STACpopulatorBase` that implements all the logic for populating a STAC catalog. This class implements an abstract method called `process_STAC_item` that should be defined in implementations of the class and contain all the logic for constructing the STAC representation for an item in the collection that is to be processed.

## Implementations

Currently, one implementation of `STACpopulatorBase` is provided in [add_CMIP6.py](implementations/add_CMIP6.py). 

## Testing

The provided `docker-compose` file can be used to launch a test STAC server. The `add_CMIP6.py` script can be run as:

```
python implementations/add_CMIP6.py http://localhost:8880/stac/ https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/simulations/bias_adjusted/catalog.html implementations/CMIP6.yml
```
Note: in the script above, I am currently using a sample THREDDS catalog URL and not one relevant to the global scale CMIP6 data.