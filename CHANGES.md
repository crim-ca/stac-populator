# Changes

## [Unreleased](https://github.com/crim-ca/stac-populator) (latest)

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
