# Changes

## [Unreleased](https://github.com/crim-ca/stac-populator) (latest)

<!-- insert list items of new changes here -->

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
