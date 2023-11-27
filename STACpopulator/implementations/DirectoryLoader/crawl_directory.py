import argparse
import os.path
from typing import NoReturn, Optional, MutableMapping, Any

from requests.sessions import Session

from STACpopulator.cli import add_request_options, apply_request_options
from STACpopulator.input import STACDirectoryLoader
from STACpopulator.models import GeoJSONPolygon, STACItemProperties
from STACpopulator.populator_base import STACpopulatorBase
from STACpopulator.stac_utils import get_logger

LOGGER = get_logger(__name__)


class DirectoryPopulator(STACpopulatorBase):
    item_properties_model = STACItemProperties
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
        self._collection_info = self._collection
        return self._collection_info

    def create_stac_collection(self) -> MutableMapping[str, Any]:
        self.publish_stac_collection(self._collection_info)
        return self._collection_info

    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        return item_data


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Directory STAC populator")
    parser.add_argument("stac_host", type=str, help="STAC API URL.")
    parser.add_argument("directory", type=str, help="Path to a directory structure with STAC Collections and Items.")
    parser.add_argument("--update", action="store_true", help="Update collection and its items.")
    parser.add_argument(
        "--prune", action="store_true",
        help="Limit search of STAC Collections only to first top-most matches in the crawled directory structure."
    )
    add_request_options(parser)
    return parser


def runner(ns: argparse.Namespace) -> Optional[int] | NoReturn:
    LOGGER.info(f"Arguments to call: {vars(ns)}")

    with Session() as session:
        apply_request_options(session, ns)
        for collection_path, collection_json in STACDirectoryLoader(ns.directory, "collection", ns.prune):
            collection_dir = os.path.dirname(collection_path)
            loader = STACDirectoryLoader(collection_dir, "item", prune=ns.prune)
            populator = DirectoryPopulator(ns.stac_host, loader, ns.update, collection_json, session=session)
            populator.ingest()


def main(*args: str) -> Optional[int]:
    parser = make_parser()
    ns = parser.parse_args(args or None)
    return runner(ns)


if __name__ == "__main__":
    main()
