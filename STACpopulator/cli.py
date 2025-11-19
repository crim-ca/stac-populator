import argparse
import functools
import importlib
import sys
import warnings
from pathlib import Path
from typing import get_args

import pystac
import requests

import STACpopulator.implementations
from STACpopulator import __version__
from STACpopulator.collection_update import UpdateModes, update_api_collection
from STACpopulator.exceptions import STACPopulatorError
from STACpopulator.export import export_catalog
from STACpopulator.log import add_logging_options, setup_logging
from STACpopulator.populators import STACpopulatorBase
from STACpopulator.request_utils import add_request_options, apply_request_options


def add_parser_args(parser: argparse.ArgumentParser) -> None:
    """Add parser arguments to the argument parser."""
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="prints the version of the library and exits",
    )
    add_logging_options(parser)
    add_request_options(parser)
    commands_subparser = parser.add_subparsers(
        title="command", dest="command", description="STAC populator command to execute.", required=True
    )
    run_parser = commands_subparser.add_parser("run", description="Run a STACpopulator implementation")
    run_parser.add_argument(
        "--stac-version",
        help="Sets the STAC version that should be used. This must match the version used by "
        "the STAC server that is being populated. This can also be set by setting the "
        "'PYSTAC_STAC_VERSION_OVERRIDE' environment variable. "
        f"Default is {pystac.get_stac_version()}",
    )
    populators_subparser = run_parser.add_subparsers(
        title="populator", dest="populator", description="Implementation to run."
    )
    for name, populator in populators().items():
        implementation_parser = populators_subparser.add_parser(name)
        implementation_parser.description = getattr(populator, "description", name)
        populator.update_parser_args(implementation_parser)
    update_parser = commands_subparser.add_parser(
        "update-collection", description="Update collection information based on items in the collection"
    )
    update_parser.add_argument("stac-collection-uri", help="URI of collection to update from a STAC API instance")
    update_parser.add_argument(
        "--mode",
        choices=get_args(UpdateModes),
        default="all",
        help="Choose whether to update summaries, extents, or all (both).",
    )
    update_parser.add_argument(
        "--exclude-summary",
        nargs="*",
        action="extend",
        default=[],
        help="Exclude these properties when updating collection summaries. ",
    )
    export_parser = commands_subparser.add_parser("export", description="Export a STAC catalog to JSON files on disk.")
    export_parser.add_argument("stac_host", help="STAC API URL")
    export_parser.add_argument("directory", type=str, help="Path to a directory to write STAC catalog contents.")
    export_parser.add_argument("-r", "--resume", action="store_true", help="Resume a partial download.")
    export_parser.add_argument(
        "--ignore-duplicate-ids",
        action="store_true",
        help="Do not raise an error if STAC items with the same ids are found in a collection.",
    )


@functools.cache
def populators() -> dict[str, STACpopulatorBase]:
    """
    Try to load implementations.

    If one fails (i.e. due to missing dependencies) continue loading others.
    """
    impl_path = Path(STACpopulator.implementations.__path__[0])
    for path in impl_path.glob("**/*.py"):
        if path.name == "__init__.py":
            path = path.parent
        rel_path = path.relative_to(impl_path)
        if str(rel_path) != ".":
            module_path = str(rel_path.with_suffix("")).replace("/", ".").replace("-", "_")
            try:
                importlib.import_module(f"STACpopulator.implementations.{module_path}")
            except STACPopulatorError as e:
                warnings.warn(f"Could not load extension {rel_path} because of error {e}")
    return {getattr(klass, "name", klass.__name__): klass for klass in STACpopulatorBase.concrete_subclasses()}


def run(ns: argparse.Namespace) -> int:
    """Run a given implementation given the arguments passed on the command line."""
    setup_logging(ns)
    with requests.Session() as session:
        apply_request_options(session, ns)
        if ns.command == "run":
            if ns.stac_version:
                pystac.set_stac_version(ns.stac_version)
            return populators()[ns.populator].run(ns, session) or 0
        elif ns.command == "update_collection":
            return update_api_collection(ns.mode, ns.stac_collection_uri, ns.exclude_summary) or 0
        else:
            return export_catalog(ns.directory, ns.stac_host, session, ns.resume, ns.ignore_duplicate_ids) or 0


def main(*args: str) -> int:
    """Run this CLI."""
    parser = argparse.ArgumentParser()
    add_parser_args(parser)
    ns = parser.parse_args(args or None)
    return run(ns)


if __name__ == "__main__":
    sys.exit(main())
