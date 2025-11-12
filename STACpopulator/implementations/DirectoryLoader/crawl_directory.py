import argparse
import inspect
import logging
import os.path
from typing import Any, Iterable, MutableMapping, Optional

import requests
from requests.sessions import Session

from STACpopulator.collection_update import UpdateModesOptional
from STACpopulator.input import STACDirectoryLoader
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populators import STACpopulatorBase

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
        update_collection: UpdateModesOptional = "none",
        exclude_summaries: Iterable[str] = (),
    ) -> None:
        self._collection = collection
        super().__init__(
            stac_host,
            loader,
            update=update,
            session=session,
            update_collection=update_collection,
            exclude_summaries=exclude_summaries,
        )

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

    @classmethod
    def update_parser_args(cls, parser: argparse.ArgumentParser) -> None:
        """Add additional CLI arguments to the argument parser."""
        super().update_parser_args(parser)
        parser.add_argument(
            "directory", type=str, help="Path to a directory structure with STAC Collections and Items."
        )
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

    @classmethod
    def run(cls, ns: argparse.Namespace, session: requests.Session) -> int:
        """Run the populator given the arguments from the command line."""
        for _, collection_path, collection_json in STACDirectoryLoader(
            ns.directory, "collection", ns.item_pattern, ns.collection_pattern, ns.prune
        ):
            collection_dir = os.path.dirname(collection_path)
            loader = STACDirectoryLoader(collection_dir, "item", ns.item_pattern, ns.collection_pattern, ns.prune)
            populator = cls(ns.stac_host, loader, ns.update, collection_json, session=session)
            populator.ingest()
        return 0
