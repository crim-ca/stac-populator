import argparse
import json
import logging
import os
import sys
import warnings
from typing import Any, MutableMapping, Optional, Union

import pystac
from pystac import STACValidationError
from pystac.extensions.datacube import DatacubeExtension
from requests.sessions import Session

from STACpopulator import cli
from STACpopulator.extensions.cmip6 import CMIP6Helper, CMIP6Properties
from STACpopulator.extensions.datacube import DataCubeHelper
from STACpopulator.extensions.thredds import THREDDSExtension, THREDDSHelper
from STACpopulator.input import ErrorLoader, GenericLoader, THREDDSLoader
from STACpopulator.log import add_logging_options
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populator_base import STACpopulatorBase
from STACpopulator.request_utils import add_request_options, apply_request_options

LOGGER = logging.getLogger(__name__)


class CMIP6populator(STACpopulatorBase):
    """Populator that creates STAC objects representing CMIP6 data from a THREDDS catalog."""

    item_properties_model = CMIP6Properties
    item_geometry_model = GeoJSONPolygon

    def __init__(
        self,
        stac_host: str,
        data_loader: GenericLoader,
        update: Optional[bool] = False,
        session: Optional[Session] = None,
        config_file: Optional[Union[os.PathLike[str], str]] = None,
    ) -> None:
        super().__init__(stac_host, data_loader, update=update, session=session, config_file=config_file)

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


def add_parser_args(parser: argparse.ArgumentParser) -> None:
    """Add additional CLI arguments to the argument parser."""
    parser.description = "CMIP6 STAC populator from a THREDDS catalog or NCML XML."
    parser.add_argument("stac_host", help="STAC API URL")
    parser.add_argument("href", help="URL to a THREDDS catalog or a NCML XML with CMIP6 metadata.")
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
    parser.add_argument(
        "--stac-version",
        help="Sets the STAC version that should be used. This must match the version used by "
        "the STAC server that is being populated. This can also be set by setting the "
        "'PYSTAC_STAC_VERSION_OVERRIDE' environment variable. "
        f"Default is {pystac.get_stac_version()}",
    )
    add_request_options(parser)
    add_logging_options(parser)


def runner(ns: argparse.Namespace) -> int:
    """Run the populator."""
    LOGGER.info(f"Arguments to call: {vars(ns)}")

    if ns.stac_version:
        pystac.set_stac_version(ns.stac_version)

    with Session() as session:
        apply_request_options(session, ns)
        if ns.mode == "full":
            data_loader = THREDDSLoader(ns.href, session=session)
        else:
            # To be implemented
            data_loader = ErrorLoader()

        c = CMIP6populator(ns.stac_host, data_loader, update=ns.update, session=session, config_file=ns.config)
        c.ingest()
    return 0


def main(*args: str) -> int:
    """Call this implementation directly."""
    warnings.warn(
        "Calling implementation scripts directly is deprecated. Please use the 'stac-populator' CLI instead.",
        DeprecationWarning,
    )
    parser = argparse.ArgumentParser()
    add_parser_args(parser)
    ns = parser.parse_args(args or None)
    ns.populator = os.path.basename(os.path.dirname(__file__))
    ns.command = "run"
    return cli.run(ns)


if __name__ == "__main__":
    sys.exit(main())
