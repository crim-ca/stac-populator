# Changes

## [Unreleased](https://github.com/crim-ca/stac-populator) (latest)

* Include `PYESSV_ARCHIVE_HOME` environment variable in Dockerfile.
* Remove redundant CLI arguments.
* Fix bug in `THREDDSLoader` iterator introduced in 0.8.0. Simple iteration over `catalog_refs` returns the catalog names (strings), whereas we want an object with a `follow` method. 
* Remove `log_debug` option from the `CORDEXCMIP6_Ouranos` runner. 
* Add attributes to CORDEX IDs to avoid duplicate IDs in the STAC catalog.
* Update test data for `CORDEXCMIP6_Ouranos`.
* Add default `create_uid` to `THREDDSCatalogDataModel`.
* Fix bug in `DataCubeHelper` for vertical coordinate extents.
* Split and clean script to update test data. 
* Add tests for RDPS and HRDPS attributes with no custom extension. 

## [0.8.0](https://github.com/crim-ca/stac-populator/tree/0.8.0) (2025-06-11)

* Add `cordex6` extension and `CORDEX-CMIP6_Ouranos` implementation. This includes a refactoring of base extension classes.
* Add an `xscen` extension demonstrating how to add properties to a STAC Item.
* Fix mismatch between CMIP6 schema URI given to `pystac` and the actual schema URI
* Add ability to export data from a STAC catalog or API to files on disk.
* Fix code that raised warnings from dependencies.
* Log to stderr only by default and to a file only if requested.
* Reorganize command line arguments to ensure shared options are always applied.
* Remove option to call implementation scripts directly from the command line.
* Remove files in the `.deprecated` folder.
* Add support for THREDDS services added in version 5.
* Fix bug where session details weren't being used to access THREDDS catalogs.
* Remove `title` from THREDDS catalog links since the content was specific to Marble.
* Change link `type` from THREDDS catalog link from `text/xml` to `application/xml` (STAC API doesn't support `text/xml` anymore).
* Support THREDDS datasets that don't contain an `NCML` access url.
* Support nested collections when loading STAC objects with the `DirectoryLoader`.
* `DirectoryLoader` now supports loading STAC objects created by the `export` command.

## [0.7.0](https://github.com/crim-ca/stac-populator/tree/0.7.0) (2025-03-07)

* Make sure *bounds* variables are given the auxiliary type attribute. 
* Fix for variables that have no attributes.
* Adding ability to add collection level assets
* Adding ability to add collection level links
* Adding collection links to `CMIP6_UofT`
* Adding an end date to `CMIP6_UofT`'s temporal extent for better rendering in STAC Browser
* Updates to datacube extension helper routines for `CMIP6_UofT`.
* Make pyessv-archive a requirement for *only* the cmip6 implementation instead of for the whole CLI
* Fix bug where logger setup failed
* Simplify CLI argument constructor code (for cleaner and more testable code)
* Add tests for CLI and implementations when invoked through the CLI
* Refactored code dealing with requests and authentication to the `STACpopulator/requests.py` file
* Add `--log-file` command line option to specify a non-default location to write log files to
* fix incorrect example in README
* move argument parsing for logging options to the implementation code
* fix bug where logging options were being set incorrectly
* rename files to avoid potential naming conflicts with other packages (`logging` and `requests`)
* Deprecate calling implementation scripts directly
* Fix bug where populator scripts could not be called directly from the command line
* Enforce versions for dependencies so that new installs won't fail unexpectedly
* Update tests to allow for a variable `stac_version` field in STAC item and collections
* Fix inconsistent defaults for parameters that update stac items and collections
* Add `--stac-version` command line option to specify the version used by the STAC server that is being populated
* add `ruff` as a dev dependency to format and lint files
* add `pre-commit` as a dev dependency to run `ruff` on commit and a workflow to run it on github as well



## [0.6.0](https://github.com/crim-ca/stac-populator/tree/0.6.0) (2024-02-22)


* Add validation to the STAC Items in `CMIP6_UofT` implementation.
* Replace CMIP6 JSON-schema URL to
  `"https://raw.githubusercontent.com/dchandan/stac-extension-cmip6/main/json-schema/schema.json"`
  for a more up-to-date validation of available STAC CMIP6 properties.
* Add `.jsonl` logging and error reporting of failed STAC Item publishing to the server.
* Improve logging configuration setup and level selection from CLI `--debug` argument.
* Fix a bug related to `THREDDSLoader` incorrectly handling the depth of crawled directories.

## [0.5.0](https://github.com/crim-ca/stac-populator/tree/0.5.0) (2024-01-09)


* Refactor CMIP6 implementation using distinct classes to define THREDDS helper utilities and the CMIP6 STAC Extension
  using the same implementation strategy as other [`pystac`](https://github.com/stac-utils/pystac) extensions.
* Add additional CMIP6 STAC Extension definitions to support STAC Collections, Items and Assets properties validation.
* Update README with a table providing missing `DirectoryLoader` implementation and adding `CMIP6_UofT` description.

## [0.4.0](https://github.com/crim-ca/stac-populator/tree/0.4.0) (2023-11-27)


* Replace logic to resolve and load specific implementation configuration file of a populator to avoid depending on
  inconsistent caller (`python <impl-module.py>` vs `stac-populator run <impl>`).
* Fix configuration file of populator implementation not found when package is installed.
* Allow a populator implementation to override the desired configuration file.
* Add missing CLI `default="full"` mode for `CMIP6_UofT` populator implementation.
* Fix Docker entrypoint to use `stac-populator` to make call to the CLI more convenient.
* Add `get_logger` function to avoid repeated configuration across modules.
* Make sure that each implementation and module employs their own logger.

## [0.3.0](https://github.com/crim-ca/stac-populator/tree/0.3.0) (2023-11-16)


* Add request ``session`` keyword to all request-related functions and populator methods to allow sharing a common set
  of settings (`auth`, SSL `verify`, `cert`) across requests toward the STAC Catalog.
* Add `DirectoryLoader` that allows populating a STAC Catalog with Collections and Items loaded from a crawled directory
  hierarchy that contains `collection.json` files and other `.json`/`.geojson` items.
* Add a generic CLI `stac-populator` that can be called to run populator implementations directly
  using command `stac-populator run <implementation> [impl-args]`.
* Remove hardcoded `verify=False` to requests calls.
  If needed for testing purposes, users should use a custom `requests.sessions.Session` with `verify=False` passed to
  the populator, or alternatively, employ the CLI argument `--no-verify` that will accomplish the same behavior.

## [0.2.0](https://github.com/crim-ca/stac-populator/tree/0.2.0) (2023-11-10)


* Add `LICENSE` file.
* Add `bump-my-version` with `make version` and `make VERSION=<...> bump` utilities to self-update release versions.
* Add more metadata to `pyproject.toml`.
* Adjust `README.md` with updated references and release version indicators.
* Add `CHANGES.md` to record version updates.
* Add `dev` dependencies to `pyproject.toml` for testing the package (install with `pip install ".[dev]"`).
* Add GitHub CI tests.
* Remove `requirements.txt` in favor of all dependencies combined in `pyproject.toml`.
* Add test to validate STAC Collection and Item contain `source` with expected THREDDS format.
* Fix broken tests and invalid imports.

## [0.1.0](https://github.com/crim-ca/stac-populator/tree/0.1.0) (2023-11-08)


* Refactor of `CMIP6_UofT` with more robust parsing strategies and STAC Item generation from THREDDS NCML metadata.

## [0.0.1](https://github.com/crim-ca/stac-populator/tree/0.0.1) (2023-08-22)

* Initial release with implementation of `CMIP6_UofT`.
