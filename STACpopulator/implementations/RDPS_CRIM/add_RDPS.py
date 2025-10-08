import argparse
import json
import logging
import os
from typing import Any, MutableMapping, Optional, Union

from pystac import STACValidationError
from pystac.extensions.datacube import DatacubeExtension
from pystac.extensions.file import FileExtension
from requests.sessions import Session

from STACpopulator.extensions.cf import CFExtension, CFHelper
from STACpopulator.extensions.datacube import DataCubeHelper
from STACpopulator.extensions.file import FileHelper
from STACpopulator.extensions.rdps import RDPSHelper, RDPSProperties
from STACpopulator.extensions.thredds import THREDDSExtension, THREDDSHelper
from STACpopulator.input import ErrorLoader, GenericLoader, THREDDSLoader
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populator_base import STACpopulatorBase

LOGGER = logging.getLogger(__name__)


class RDPSpopulator(STACpopulatorBase):
    """Populator that creates STAC objects representing RDPS data from a THREDDS catalog."""

    item_properties_model = RDPSProperties
    item_geometry_model = GeoJSONPolygon

    def __init__(
        self,
        stac_host: str,
        data_loader: GenericLoader,
        update: Optional[bool] = False,
        session: Optional[Session] = None,
        config_file: Optional[Union[os.PathLike[str], str]] = None,
    ) -> None:
        super().__init__(
            stac_host,
            data_loader,
            update=update,
            session=session,
            config_file=config_file,
        )

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
        # Add RDPS extension
        try:
            rdps_helper = RDPSHelper(item_data, self.item_geometry_model)
            item = rdps_helper.stac_item()
        except Exception as e:
            raise Exception("Failed to add RDPS extension") from e

        # Add DataCube Extension
        try:
            datacube_helper = DataCubeHelper(item_data)
            datacube_ext = DatacubeExtension.ext(item, add_if_missing=True)
            datacube_ext.apply(
                dimensions=datacube_helper.dimensions,
                variables=datacube_helper.variables,
            )
        except Exception as e:
            raise Exception("Failed to add Datacube extension") from e

        # Add THREDDS Extension
        try:
            thredds_helper = THREDDSHelper(item_data["access_urls"])
            thredds_ext = THREDDSExtension.ext(item)
            thredds_ext.apply(thredds_helper.services, thredds_helper.links)
        except Exception as e:
            raise Exception("Failed to add THREDDS extension") from e

        asset = item.assets["HTTPServer"]
        # Add CF Extension
        try:
            cf_helper = CFHelper(item_data["variables"])
            cf_item_ext = CFExtension.ext(item, add_if_missing=True)
            cf_item_ext.apply(cf_helper.parameters)

            cf_asset_ext = CFExtension.ext(asset, add_if_missing=True)
            cf_asset_ext.apply(cf_helper.parameters)
        except Exception as e:
            raise Exception("Failed to add CF extension") from e

        try:
            file_helper = FileHelper(asset.get_absolute_href())
            file_ext = FileExtension.ext(asset, add_if_missing=True)
            file_ext.apply(
                byte_order=file_helper.byte_order,
                checksum=file_helper.checksum,  # FIXME: Displayed as n/a on browser
                header_size=0,  # FIXME: clarify expected value here
                size=file_helper.size,
                values=None,  # NOTE: deprecated
                local_path=None,  # FIXME: clarify expected value here
            )
        except Exception as e:
            raise Exception("Failed to add Asset File extension") from e

        try:
            item.validate()
        except STACValidationError as e:
            print(json.dumps(item.to_dict()))
            raise Exception("Failed to validate STAC item") from e

        return json.loads(json.dumps(item.to_dict()))


def add_parser_args(parser: argparse.ArgumentParser) -> None:
    """Add additional CLI arguments to the argument parser."""
    parser.description = "RDPS STAC populator from a THREDDS catalog or NCML XML."
    parser.add_argument("stac_host", help="STAC API URL")
    parser.add_argument("href", help="URL to a THREDDS catalog or a NCML XML with RDPS metadata.")
    parser.add_argument("--update", action="store_true", help="Update collection and its items")
    parser.add_argument(
        "--mode",
        choices=["full", "single"],
        default="full",
        help="Operation mode, processing the full dataset or only the single reference.",
    )
    parser.add_argument(
        "--config",
        type=str,
        help=(
            "Override configuration file for the populator. "
            "By default, uses the adjacent configuration to the implementation class."
        ),
    )


def runner(ns: argparse.Namespace, session: Session) -> int:
    """Run the populator."""
    LOGGER.info(f"Arguments to call: {vars(ns)}")

    if ns.mode == "full":
        data_loader = THREDDSLoader(ns.href, session=session)
    else:
        # To be implemented
        data_loader = ErrorLoader()

    c = RDPSpopulator(
        ns.stac_host,
        data_loader,
        update=ns.update,
        session=session,
        config_file=ns.config,
    )
    c.ingest()
    return 0
