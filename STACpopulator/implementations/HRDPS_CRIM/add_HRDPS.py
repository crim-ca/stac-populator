import logging
from typing import Any

from STACpopulator.extensions.hrdps import HRDPSDataModel
from STACpopulator.populators import THREDDSPopulator

LOGGER = logging.getLogger(__name__)


class HRDPSpopulator(THREDDSPopulator):
    """Populator that creates STAC objects representing HRDPS data from a THREDDS catalog."""

    name = "HRDPS_CRIM"
    description = "HRDPS STAC populator from a THREDDS catalog or NCML XML."
    data_model = HRDPSDataModel

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Return a STAC item."""
        dm = self.data_model.from_data(item_data)
        return dm.stac_item()
