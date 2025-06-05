import argparse
import inspect
import logging
import os.path
import sys
import warnings
from typing import Any, MutableMapping, Optional

import pystac
from requests.sessions import Session

from STACpopulator import cli
from STACpopulator.input import STACDirectoryLoader
from STACpopulator.log import add_logging_options
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populator_base import STACpopulatorBase
from STACpopulator.request_utils import add_request_options, apply_request_options

LOGGER = logging.getLogger(__name__)


class DirectoryPopulator(STACpopulatorBase):
    """Populator that constructs STAC objects from files in a directory."""

    item_geometry_model = GeoJSONPolygon

    def __init__(
        self,
        stac_host: str,
        loader: STACDirectoryLoader,
        update: bool,
        collection: dict[str, Any],
        session: Optional[Session] = None,
    ) -> None:
        self._collection = collection
        super().__init__(stac_host, loader, update=update, session=session)

    def load_config(self) -> MutableMapping[str, Any]:
        """Load configuration options."""
        self._collection_info = self._collection
        return self._collection_info

    def create_stac_collection(self) -> MutableMapping[str, Any]:
        """Return a STAC collection."""
        self.publish_stac_collection(self._collection_info)
        return self._collection_info

    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        """Return a STAC item."""
        return item_data


def add_parser_args(parser: argparse.ArgumentParser) -> None:
    """Add additional CLI arguments to the argument parser."""
    parser.description = "Directory STAC populator"
    parser.add_argument("stac_host", type=str, help="STAC API URL.")
    parser.add_argument("directory", type=str, help="Path to a directory structure with STAC Collections and Items.")
    parser.add_argument("--update", action="store_true", help="Update collection and its items.")
    dirloader_init_params = inspect.signature(STACDirectoryLoader.__init__).parameters
    parser.add_argument(
        "--collection-pattern",
        help="regex pattern used to identify files that contain STAC collections. Default is '%(default)s'",
        default=dirloader_init_params["collection_pattern"].default,
    )
    parser.add_argument(
        "--item-pattern",
        help="regex pattern used to identify files that contain STAC items. Default is '%(default)s'",
        default=dirloader_init_params["item_pattern"].default,
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Limit search of STAC Collections only to first top-most matches in the crawled directory structure.",
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
        for _, collection_path, collection_json in STACDirectoryLoader(
            ns.directory, "collection", ns.item_pattern, ns.collection_pattern, ns.prune
        ):
            collection_dir = os.path.dirname(collection_path)
            loader = STACDirectoryLoader(collection_dir, "item", ns.item_pattern, ns.collection_pattern, ns.prune)
            populator = DirectoryPopulator(ns.stac_host, loader, ns.update, collection_json, session=session)
            populator.ingest()
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
