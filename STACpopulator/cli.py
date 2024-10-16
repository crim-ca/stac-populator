import argparse
import functools
import importlib
import logging
import sys
from types import ModuleType
import warnings
from typing import Callable

from STACpopulator import __version__, implementations
from STACpopulator.exceptions import STACPopulatorError
from STACpopulator.log import setup_logging


def add_parser_args(parser: argparse.ArgumentParser) -> dict[str, Callable]:
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


@functools.cache
def implementation_modules() -> dict[str, ModuleType]:
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
    if ns.command == "run":
        setup_logging(ns.log_file, ns.debug or logging.INFO)
        return implementation_modules()[ns.populator].runner(ns) or 0


def main(*args: str) -> int:
    parser = argparse.ArgumentParser()
    add_parser_args(parser)
    ns = parser.parse_args(args or None)
    return run(ns)


if __name__ == "__main__":
    sys.exit(main())
