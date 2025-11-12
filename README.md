# STAC Catalog Populator

![Latest Version](https://img.shields.io/badge/latest%20version-1.11.0-blue?logo=github)
![Commits Since Latest](https://img.shields.io/github/commits-since/crim-ca/stac-populator/1.11.0.svg?logo=github)
![GitHub License](https://img.shields.io/github/license/crim-ca/stac-populator)

This repository contains a framework [STACpopulator](STACpopulator)
that can be used to implement concrete populators (see [implementations](STACpopulator/implementations))
for populating the STAC Catalog, Collections and Items from various dataset/catalog sources, and pushed using
STAC API on a server node.

It can also be used to export data from an existing STAC API or catalog to files on disk. These can then later
be used to populate a STAC API with the `DirectoryLoader` implementation.

It can also be used to update a STAC collection's extents and/or summaries based on the STAC items that already
are part of the collection. It does this by iterating through the items in the collection and updating the
relevant collection properties accordingly.

## Framework

The framework is centered around a Python Abstract Base Class: `STACpopulatorBase` that implements all the logic
for populating a STAC catalog. This class provides abstract methods that should be overridden by implementations that
contain all the logic for constructing the STAC representation for an item in the collection that is to be processed.

## Implementations

Provided implementations of `STACpopulatorBase`:

| Implementation                               | Description                                                                                                             |
|----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [CMIP6_UofT][CMIP6_UofT]                     | Crawls a THREDDS Catalog for CMIP6 NCML-annotated NetCDF references to publish corresponding STAC Collection and Items. |
| [DirectoryLoader][DirLoader]                 | Crawls a subdirectory hierarchy of pre-generated STAC Collections and Items to publish to a STAC API endpoint.          |
| [CORDEX-CMIP6_Ouranos][CORDEX-CMIP6_Ouranos] | Crawls a THREDDS Catalog for CORDEX-CMIP6 NetCDF references to publish corresponding STAC Collection and Items.         |

[CMIP6_UofT]: STACpopulator/implementations/CMIP6_UofT/add_CMIP6.py
[DirLoader]: STACpopulator/implementations/DirectoryLoader/crawl_directory.py
[CORDEX-CMIP6_Ouranos]: STACpopulator/implementations/CORDEX-CMIP6_Ouranos/add_CORDEX-CMIP6.py

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

# obtain general help about exporting STAC catalogs to a directory on disk
stac-populator export --help

# obtain general help about updating STAC collections based on their items
stac-populator update-collection --help
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
docker run -ti ghcr.io/crim-ca/stac-populator:1.11.0 [command]
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

For more tests validation, you can also run the test suite with coverage analysis.

```shell
make test-cov
```

## Contributing

We welcome any contributions to this codebase. To submit suggested changes, please do the following:

- create a new feature branch off of `master`
- update the code, write/update tests, write/update documentation
- submit a pull request targetting the `master` branch

### Coding Style

This codebase uses the [`ruff`](https://docs.astral.sh/ruff/) formatter and linter to enforce style policies.

To check that your changes conform to these policies please run:

```sh
ruff format
ruff check
```

You can also set up pre-commit hooks that will run these checks before you create any commit in this repo:

```sh
pre-commit install
```

### Writing tests

Unit tests use the [pytest-recording](https://github.com/kiwicom/pytest-recording) package to cache
network responses. This allows the tests to be run offline and allows them to reliably pass regardless of
whether a remote resource is available or not.

Whenever you're writing tests that make a request to an external resource, please use the `@pytest.mark.vcr`
decorator and record a new cassette (response cache) which can be committed to version control with the new
tests.
