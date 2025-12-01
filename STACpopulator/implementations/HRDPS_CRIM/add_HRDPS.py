import argparse
import logging
from typing import Any

from requests.sessions import Session

from STACpopulator.extensions.hrdps import HRDPSDataModel
from STACpopulator.input import ErrorLoader, THREDDSLoader
from STACpopulator.populator_base import STACpopulatorBase

LOGGER = logging.getLogger(__name__)


class HRDPSpopulator(STACpopulatorBase):
    """Populator that creates STAC objects representing HRDPS data from a THREDDS catalog."""

    data_model = HRDPSDataModel

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Return a STAC item."""
        dm = self.data_model.from_data(item_data)
        return dm.stac_item()


def add_parser_args(parser: argparse.ArgumentParser) -> None:
    """Add additional CLI arguments to the argument parser."""
    parser.description = "HRDPS STAC populator from a THREDDS catalog or NCML XML."
    parser.add_argument("stac_host", help="STAC API URL")
    parser.add_argument("href", help="URL to a THREDDS catalog or a NCML XML with HRDPS metadata.")
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

    c = HRDPSpopulator(
        ns.stac_host,
        data_loader,
        update=ns.update,
        session=session,
        config_file=ns.config,
    )
    c.ingest()
    return 0
