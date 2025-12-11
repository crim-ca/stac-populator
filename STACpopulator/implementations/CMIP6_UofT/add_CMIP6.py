import json
import logging
from typing import Any, MutableMapping, Union

from pystac import STACValidationError
from pystac.extensions.datacube import DatacubeExtension

from STACpopulator.extensions.cmip6 import CMIP6Helper, CMIP6Properties
from STACpopulator.extensions.datacube import DataCubeHelper
from STACpopulator.extensions.thredds import THREDDSExtension, THREDDSHelper
from STACpopulator.populators import THREDDSPopulator

LOGGER = logging.getLogger(__name__)


class CMIP6populator(THREDDSPopulator):
    """Populator that creates STAC objects representing CMIP6 data from a THREDDS catalog."""

    name = "CMIP6_UofT"
    description = "CMIP6 STAC populator from a THREDDS catalog or NCML XML."

    item_properties_model = CMIP6Properties

    def create_stac_item(
        self, item_name: str, item_data: MutableMapping[str, Any]
    ) -> Union[None, MutableMapping[str, Any]]:
        """Create a STAC item.

        :param item_name: name of the STAC item. Interpretation of name is left to the input loader implementation
        :type item_name: str
        :param item_data: dictionary like representation of all information on the item
        :type item_data: MutableMapping[str, Any]
        :return: _description_
        :rtype: MutableMapping[str, Any]
        """
        # Add CMIP6 extension
        try:
            cmip_helper = CMIP6Helper(item_data)
            item = cmip_helper.stac_item()
        except Exception as e:
            raise Exception("Failed to add CMIP6 extension") from e

        # Add datacube extension
        try:
            dc_helper = DataCubeHelper(item_data)
            dc_ext = DatacubeExtension.ext(item, add_if_missing=True)
            dc_ext.apply(dimensions=dc_helper.dimensions, variables=dc_helper.variables)
        except Exception as e:
            raise Exception("Failed to add Datacube extension") from e

        try:
            thredds_helper = THREDDSHelper(item_data["access_urls"])
            thredds_ext = THREDDSExtension.ext(item)
            thredds_ext.apply(thredds_helper.services, thredds_helper.links)
        except Exception as e:
            raise Exception("Failed to add THREDDS extension") from e

        try:
            item.validate()
        except STACValidationError as e:
            raise Exception("Failed to validate STAC item") from e

        # print(json.dumps(item.to_dict()))
        return json.loads(json.dumps(item.to_dict()))
