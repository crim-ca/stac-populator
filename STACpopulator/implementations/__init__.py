# By adding modules to __all__, they are discoverable by the cli.implementation_modules method and
# become available to be invoked through the CLI.
# All modules in this list must contain two functions:
#  - add_parser_args(parser: argparse.ArgumentParser) -> None
#       - adds additional arguments to the given parser needed to run this implementation
#  - def runner(ns: argparse.Namespace) -> int:
#       - runs the implementation given a namespace constructed from the parser arguments supplied
__all__ = ["CMIP6_UofT", "DirectoryLoader", "CORDEXCMIP6_Ouranos", "RDPS_CRIM", "HRDPS_CRIM"]
