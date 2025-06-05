"""Test the creation of extensions."""

from __future__ import annotations

import datetime as dt

from STACpopulator.extensions.base import BaseSTAC, ExtensionHelper


class ExTest(ExtensionHelper):
    f: float
    n: float
    _prefix: str = "ex"


# Customize the THREDDSCatalogDataModel
class _TestDataModel(BaseSTAC):
    """Data model for CORDEX-CMIP6 NetCDF datasets."""

    ex: ExTest

    def create_uid(self) -> str:
        """Return a unique ID for CMIP6 data item."""
        return self.id


def test_extension():
    geom = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}
    model = _TestDataModel(
        id="test", geometry=geom, bbox=[0, 0, 1, 1], datetime=dt.datetime(2021, 1, 1), ex={"f": 1.0, "n": float("nan")}
    )

    assert set(model._helpers) == {"ex"}
    item = model.stac_item()
    assert item["properties"]["ex:f"] == 1.0
    assert item["properties"]["ex:n"] == "NaN"
