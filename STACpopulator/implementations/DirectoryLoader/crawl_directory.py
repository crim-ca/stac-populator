import argparse
import inspect
import logging
import os.path

from requests.sessions import Session

from STACpopulator.input import STACDirectoryLoader
from STACpopulator.populators.directory import DirectoryPopulator

LOGGER = logging.getLogger(__name__)


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


def runner(ns: argparse.Namespace, session: Session) -> int:
    """Run the populator."""
    LOGGER.info(f"Arguments to call: {vars(ns)}")

    for _, collection_path, collection_json in STACDirectoryLoader(
        ns.directory, "collection", ns.item_pattern, ns.collection_pattern, ns.prune
    ):
        collection_dir = os.path.dirname(collection_path)
        loader = STACDirectoryLoader(collection_dir, "item", ns.item_pattern, ns.collection_pattern, ns.prune)
        populator = DirectoryPopulator(
            ns.stac_host,
            loader,
            ns.update,
            collection_json,
            session=session,
            update_collection=ns.update_collection,
            exclude_summaries=ns.exclude_summary,
        )
        populator.ingest()
    return 0
