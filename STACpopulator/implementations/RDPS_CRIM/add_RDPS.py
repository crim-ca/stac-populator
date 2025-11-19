import logging
from typing import Any

from STACpopulator.extensions.rdps import RDPSDataModel
from STACpopulator.populators import THREDDSPopulator

LOGGER = logging.getLogger(__name__)


class RDPSpopulator(THREDDSPopulator):
    """Populator that creates STAC objects representing RDPS data from a THREDDS catalog."""

    data_model = RDPSDataModel
    item_geometry_model = None  # Unnecessary, but kept for consistency

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Return a STAC item."""
        dm = self.data_model.from_data(item_data, session=self._session)
        return dm.stac_item()
