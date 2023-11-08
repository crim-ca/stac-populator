# Changes

## [Unreleased](https://github.com/crim-ca/stac-populator) (latest)

* Add `LICENSE` file.
* Add `bump-my-version` with `make version` and `make VERSION=<...> bump` utilities to self-update release versions.
* Add more metadata to `pyproject.toml`.
* Adjust `README.md` with updated references and release version indicators.
* Add `CHANGES.md` to record version updates.
* Add `dev` dependencies to `pyproject.toml` for testing the package (install with `pip install ".[dev]"`).
* Remove `requirements.txt` in favor of all dependencies combined in `pyproject.toml`.
* Refactor of `CMIP6_UofT` with more robust parsing strategies and STAC Item generation from THREDDS NCML metadata.

## [0.0.1](https://github.com/crim-ca/stac-populator/tree/0.0.1) (2023-08-22)

* Initial release with implementation of `CMIP6_UofT`.
