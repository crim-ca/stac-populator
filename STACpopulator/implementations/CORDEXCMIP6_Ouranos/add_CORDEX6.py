import logging
from typing import Any

from STACpopulator.extensions.cordex6 import Cordex6DataModel
from STACpopulator.populators import THREDDSPopulator

LOGGER = logging.getLogger(__name__)


class CORDEX_STAC_Populator(THREDDSPopulator):
    """Populator that creates STAC objects representing CORDEX data from a THREDDS catalog."""

    name = "CORDEXCMIP6_Ouranos"
    description = "CMIP6-CORDEX STAC populator from a THREDDS catalog or NCML XML."

    data_model = Cordex6DataModel
    item_geometry_model = None  # Unnecessary, but kept for consistency

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Return a STAC item."""
        dm = self.data_model.from_data(item_data)
        return dm.stac_item()
