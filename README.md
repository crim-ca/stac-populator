# STAC Catalog Populator

![Latest Version](https://img.shields.io/badge/latest%20version-0.6.0-blue?logo=github)
![Commits Since Latest](https://img.shields.io/github/commits-since/crim-ca/stac-populator/0.6.0.svg?logo=github)
![GitHub License](https://img.shields.io/github/license/crim-ca/stac-populator)

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

| Implementation                 | Description                                                                                                             |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [CMIP6_UofT][CMIP6_UofT]       | Crawls a THREDDS Catalog for CMIP6 NCML-annotated NetCDF references to publish corresponding STAC Collection and Items. |
| [DirectoryLoader][DirLoader]   | Crawls a subdirectory hierarchy of pre-generated STAC Collections and Items to publish to a STAC API endpoint.          |

[CMIP6_UofT]: STACpopulator/implementations/CMIP6_UofT/add_CMIP6.py
[DirLoader]: STACpopulator/implementations/DirectoryLoader/crawl_directory.py

## Installation and Execution

Either with Python directly (in an environment of your choosing):

```shell
pip install .
# OR
make install
```

With development packages:

```shell
pip install .[dev]
# OR
make install-dev
```

You should then be able to call the STAC populator CLI with following commands:

```shell
# obtain the installed version of the STAC populator
stac-populator --version

# obtain general help about available commands
stac-populator --help

# obtain general help about available STAC populator implementations
stac-populator run --help

# obtain help specifically for the execution of a STAC populator implementation
stac-populator run [implementation] --help
```

### CMIP6 extension: extra requirements

The CMIP6 stac-populator extension requires that the [pyessv-archive](https://github.com/ES-DOC/pyessv-archive) data 
files be installed. To install this package to the default location in your home directory at `~/.esdoc/pyessv-archive`:

```shell
git clone https://github.com/ES-DOC/pyessv-archive ~/.esdoc/pyessv-archive
# OR
make setup-pyessv-archive
```

You can also choose to install them to a location on disk other than the default:

```shell
git clone https://github.com/ES-DOC/pyessv-archive /some/other/place
# OR
PYESSV_ARCHIVE_HOME=/some/other/place make setup-pyessv-archive
```

*Note*: <br>
If you have installed the [pyessv-archive](https://github.com/ES-DOC/pyessv-archive) data files to a non-default
location, you need to specify that location with the `PYESSV_ARCHIVE_HOME` environment variable. For example,
if you've installed the pyessv-archive files to `/some/other/place` then run the following before executing 
any of the example commands above:

```shell
export PYESSV_ARCHIVE_HOME=/some/other/place
```

### Docker

You can also employ the pre-built Docker, which can be called as follows,
where `[command]` corresponds to any of the above example operations.

```shell
docker run -ti ghcr.io/crim-ca/stac-populator:0.6.0 [command]
```

*Note*: <br>
If files needs to provided as input or obtained as output for using a command with `docker`, you will need to either
mount files individually or mount a workspace directory using `-v {local-path}:{docker-path}` inside the Docker
container to make them accessible to the command.

## Testing

The provided [`docker-compose`](docker/docker-compose.yml) configuration file can be used to launch a test STAC server.
Consider using `make docker-start` to start this server, and `make docker-stop` to stop it.
Alternatively, you can also use your own STAC server accessible from any remote location.

To run the STAC populator, follow the steps from [Installation and Execution](#installation-and-execution).

Alternatively, you can call the relevant populator Python scripts individually.
For example, using the [CMIP6_UofT][CMIP6_UofT] implementation, the script can be run as:

```shell
python STACpopulator/implementations/CMIP6_UofT/add_CMIP6.py \
    "http://localhost:8880/stac/" \
    "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.html" \
    --config "STACpopulator/implementations/CMIP6_UofT/collection_config.yml"
```

*Note*: <br>
In the script above, a sample THREDDS catalog URL is employed and not one relevant to the global scale CMIP6 data.

For more tests validation, you can also run the test suite with coverage analysis.

```shell
make test-cov
```
