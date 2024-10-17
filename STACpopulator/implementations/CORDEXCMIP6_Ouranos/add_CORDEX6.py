import logging
from requests.sessions import Session

from STACpopulator.requests import add_request_options, apply_request_options
from STACpopulator.input import ErrorLoader, THREDDSLoader

import argparse
from typing import Any
from STACpopulator.populator_base import STACpopulatorBase
from STACpopulator.extensions.cordex6 import Cordex6DataModel

LOGGER = logging.getLogger(__name__)


class CORDEX_STAC_Populator(STACpopulatorBase):
    data_model = Cordex6DataModel
    item_geometry_model = None  # Unnecessary, but kept for consistency

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        dm = self.data_model.from_data(item_data)
        return dm.stac_item()



# TODO: This probably doesn't need to be copied for every implementation, right ?
def add_parser_args(parser: argparse.ArgumentParser) -> None:
    parser.description="CMIP6-CORDEX STAC populator from a THREDDS catalog or NCML XML."
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
    add_request_options(parser)


def runner(ns: argparse.Namespace) -> int:
    LOGGER.info(f"Arguments to call: {vars(ns)}")

    with Session() as session:
        apply_request_options(session, ns)
        if ns.mode == "full":
            data_loader = THREDDSLoader(ns.href, session=session)
        else:
            # To be implemented
            data_loader = ErrorLoader()

        c = CORDEX_STAC_Populator(
            ns.stac_host, data_loader, update=ns.update, session=session, config_file=ns.config, log_debug=ns.debug
        )
        c.ingest()
    return 0
