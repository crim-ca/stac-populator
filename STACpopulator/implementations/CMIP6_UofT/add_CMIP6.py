import argparse
import json
from typing import Any, MutableMapping, NoReturn, Optional

from requests.sessions import Session
from pystac.extensions.datacube import DatacubeExtension

from STACpopulator.cli import add_request_options, apply_request_options
from STACpopulator.extensions.cmip6 import CMIP6Properties, CMIP6Helper
from STACpopulator.extensions.datacube import DataCubeHelper
from STACpopulator.extensions.thredds import THREDDSHelper, THREDDSExtension
from STACpopulator.input import GenericLoader, ErrorLoader, THREDDSLoader
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populator_base import STACpopulatorBase
from STACpopulator.stac_utils import LOGGER


class CMIP6populator(STACpopulatorBase):
    item_properties_model = CMIP6Properties
    item_geometry_model = GeoJSONPolygon

    def __init__(
        self,
        stac_host: str,
        data_loader: GenericLoader,
        update: Optional[bool] = False,
        session: Optional[Session] = None,
    ) -> None:
        """Constructor

        :param stac_host: URL to the STAC API
        :type stac_host: str
        """
        super().__init__(stac_host, data_loader, update=update, session=session)

    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        """Creates the STAC item.

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
        except Exception:
            LOGGER.error("Failed to add CMIP6 extension to item %s", item_name)
            raise

        # Add datacube extension
        try:
            dc_helper = DataCubeHelper(item_data)
            dc_ext = DatacubeExtension.ext(item, add_if_missing=True)
            dc_ext.apply(dimensions=dc_helper.dimensions, variables=dc_helper.variables)
        except Exception:
            LOGGER.error("Failed to add Datacube extension to item %s", item_name)
            raise

        try:
            thredds_helper = THREDDSHelper(item_data["access_urls"])
            thredds_ext = THREDDSExtension.ext(item)
            thredds_ext.apply(thredds_helper.services, thredds_helper.links)
        except Exception:
            LOGGER.error("Failed to add THREDDS references to item %s", item_name)
            raise

        # print(json.dumps(item.to_dict()))
        return json.loads(json.dumps(item.to_dict()))


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CMIP6 STAC populator from a THREDDS catalog or NCML XML.")
    parser.add_argument("stac_host", type=str, help="STAC API address")
    parser.add_argument("href", type=str, help="URL to a THREDDS catalog or a NCML XML with CMIP6 metadata.")
    parser.add_argument("--update", action="store_true", help="Update collection and its items")
    parser.add_argument("--mode", choices=["full", "single"],
                        help="Operation mode, processing the full dataset or only the single reference.")
    add_request_options(parser)
    return parser


def runner(ns: argparse.Namespace) -> Optional[int] | NoReturn:
    LOGGER.info(f"Arguments to call: {vars(ns)}")

    with Session() as session:
        apply_request_options(session, ns)
        if ns.mode == "full":
            data_loader = THREDDSLoader(ns.href, session=session)
        else:
            # To be implemented
            data_loader = ErrorLoader()

        c = CMIP6populator(ns.stac_host, data_loader, update=ns.update, session=session)
        c.ingest()


def main(*args: str) -> Optional[int]:
    parser = make_parser()
    ns = parser.parse_args(args or None)
    return runner(ns)


if __name__ == "__main__":
    main()
