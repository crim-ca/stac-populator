from typing import Any

from STACpopulator.datamodels.hrdps import HRDPSDataModel
from STACpopulator.populators.base import STACpopulatorBase


class HRDPSpopulator(STACpopulatorBase):
    """Populator that creates STAC objects representing HRDPS data from a THREDDS catalog."""

    data_model = HRDPSDataModel
    item_geometry_model = None  # Unnecessary, but kept for consistency

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Return a STAC item."""
        dm = self.data_model.from_data(item_data)
        return dm.stac_item()
