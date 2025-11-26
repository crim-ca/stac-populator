import json
from typing import Any, MutableMapping, Union

from pystac import STACValidationError
from pystac.extensions.datacube import DatacubeExtension

from STACpopulator.extensions.cmip6 import CMIP6Properties
from STACpopulator.extensions.thredds import THREDDSExtension
from STACpopulator.helpers.cmip6 import CMIP6Helper
from STACpopulator.helpers.datacube import DataCubeHelper
from STACpopulator.helpers.thredds import THREDDSHelper
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populators.base import STACpopulatorBase


class CMIP6populator(STACpopulatorBase):
    """Populator that creates STAC objects representing CMIP6 data from a THREDDS catalog."""

    item_properties_model = CMIP6Properties
    item_geometry_model = GeoJSONPolygon

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
            cmip_helper = CMIP6Helper(item_data, self.item_geometry_model)
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
