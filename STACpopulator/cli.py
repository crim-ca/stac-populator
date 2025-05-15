import argparse
import functools
import importlib
import logging
import sys
import warnings
from types import ModuleType

import requests

from STACpopulator import __version__, implementations
from STACpopulator.exceptions import STACPopulatorError
from STACpopulator.export import export_catalog
from STACpopulator.log import add_logging_options, setup_logging
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
    commands_subparser = parser.add_subparsers(
        title="command", dest="command", description="STAC populator command to execute.", required=True
    )
    run_parser = commands_subparser.add_parser("run", description="Run a STACpopulator implementation")
    populators_subparser = run_parser.add_subparsers(
        title="populator", dest="populator", description="Implementation to run."
    )
    for implementation_module_name, module in implementation_modules().items():
        implementation_parser = populators_subparser.add_parser(implementation_module_name)
        module.add_parser_args(implementation_parser)
    export_parser = commands_subparser.add_parser("export", description="Export a STAC catalog to JSON files on disk.")
    export_parser.add_argument("stac_host", help="STAC API URL")
    export_parser.add_argument("directory", type=str, help="Path to a directory to write STAC catalog contents.")
    export_parser.add_argument(
        "-c", "--continue", action="store_true", dest="continue_", help="Continue a partial download."
    )
    add_request_options(export_parser)
    add_logging_options(export_parser)


@functools.cache
def implementation_modules() -> dict[str, ModuleType]:
    """
    Try to load implementations.

    If one fails (i.e. due to missing dependencies) continue loading others.
    """
    modules = {}
    for implementation_module_name in implementations.__all__:
        try:
            modules[implementation_module_name] = importlib.import_module(
                f".{implementation_module_name}", implementations.__package__
            )
        except STACPopulatorError as e:
            warnings.warn(f"Could not load extension {implementation_module_name} because of error {e}")
    return modules


def run(ns: argparse.Namespace) -> int:
    """Run a given implementation given the arguments passed on the command line."""
    setup_logging(ns.log_file, ns.debug or logging.INFO)
    if ns.command == "run":
        return implementation_modules()[ns.populator].runner(ns) or 0
    else:
        with requests.Session() as session:
            apply_request_options(session, ns)
            return export_catalog(ns.directory, ns.stac_host, session, ns.continue_) or 0


def main(*args: str) -> int:
    """Run this CLI."""
    parser = argparse.ArgumentParser()
    add_parser_args(parser)
    ns = parser.parse_args(args or None)
    return run(ns)


if __name__ == "__main__":
    sys.exit(main())
