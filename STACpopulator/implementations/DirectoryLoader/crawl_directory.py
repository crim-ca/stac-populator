import argparse
import logging
import os.path
from typing import Any, MutableMapping, Optional

import pystac
from requests.sessions import Session

from STACpopulator.input import STACDirectoryLoader
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populator_base import STACpopulatorBase

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


def runner(ns: argparse.Namespace, session: Session) -> int:
    """Run the populator."""
    LOGGER.info(f"Arguments to call: {vars(ns)}")

    if ns.stac_version:
        pystac.set_stac_version(ns.stac_version)

    for _, collection_path, collection_json in STACDirectoryLoader(ns.directory, "collection", ns.prune):
        collection_dir = os.path.dirname(collection_path)
        loader = STACDirectoryLoader(collection_dir, "item", prune=ns.prune)
        populator = DirectoryPopulator(ns.stac_host, loader, ns.update, collection_json, session=session)
        populator.ingest()
    return 0
