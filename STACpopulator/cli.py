import argparse
import glob
import importlib
import os
import sys
from typing import Callable, Optional

import requests
from http import cookiejar
from requests.auth import AuthBase, HTTPBasicAuth, HTTPDigestAuth, HTTPProxyAuth
from requests.sessions import Session

from STACpopulator import __version__

POPULATORS = {}


class HTTPBearerTokenAuth(AuthBase):
    def __init__(self, token: str) -> None:
        self._token = token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        r.headers["Authorization"] = f"Bearer {self._token}"
        return r


class HTTPCookieAuth(AuthBase):
    """
    Employ a cookie-jar file for authorization.

    Useful command:

    .. code-block:: shell

        curl --cookie-jar /path/to/cookie-jar.txt [authorization-provider-arguments]

    """
    def __init__(self, cookie_jar: str) -> None:
        self._cookie_jar = cookie_jar

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        r.prepare_cookies(cookiejar.FileCookieJar(self._cookie_jar))
        return r


def add_request_options(parser: argparse.ArgumentParser) -> None:
    """
    Adds arguments to a parser to allow update of a request session definition used across a populator procedure.
    """
    parser.add_argument(
        "--no-verify", "--no-ssl", "--no-ssl-verify", dest="verify", action="store_false",
        help="Disable SSL verification (not recommended unless for development/test servers)."
    )
    parser.add_argument(
        "--cert", type=argparse.FileType(), required=False, help="Path to a certificate file to use."
    )
    parser.add_argument(
        "--auth-handler", choices=["basic", "digest", "bearer", "proxy", "cookie"], required=False,
        help="Authentication strategy to employ for the requests session."
    )
    parser.add_argument(
        "--auth-identity", required=False,
        help="Bearer token, cookie-jar file or proxy/digest/basic username:password for selected authorization handler."
    )


def apply_request_options(session: Session, namespace: argparse.Namespace) -> None:
    """
    Applies the relevant request session options from parsed input arguments.
    """
    session.verify = namespace.verify
    session.cert = namespace.cert
    if namespace.auth_handler in ["basic", "digest", "proxy"]:
        usr, pwd = namespace.auth_identity.split(":", 1)
        if namespace.auth_handler == "basic":
            session.auth = HTTPBasicAuth(usr, pwd)
        elif namespace.auth_handler == "digest":
            session.auth = HTTPDigestAuth(usr, pwd)
        else:
            session.auth = HTTPProxyAuth(usr, pwd)
    elif namespace.auth_handler == "bearer":
        session.auth = HTTPBearerTokenAuth(namespace.auth_identity)
    elif namespace.auth_handler == "cookie":
        session.auth = HTTPCookieAuth(namespace.auth_identity)


def make_main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stac-populator", description="STACpopulator operations.")
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}",
                        help="prints the version of the library and exits")
    commands = parser.add_subparsers(title="command", dest="command", description="STAC populator command to execute.")

    run_cmd_parser = make_run_command_parser(parser.prog)
    commands.add_parser(
        "run",
        prog=f"{parser.prog} {run_cmd_parser.prog}", parents=[run_cmd_parser],
        formatter_class=run_cmd_parser.formatter_class, usage=run_cmd_parser.usage,
        add_help=False, help=run_cmd_parser.description, description=run_cmd_parser.description
    )

    # add more commands as needed...

    return parser


def make_run_command_parser(parent) -> argparse.ArgumentParser:
    """
    Groups all sub-populator CLI listed in :py:mod:`STACpopulator.implementations` as a common ``stac-populator`` CLI.

    Dispatches the provided arguments to the appropriate sub-populator CLI as requested. Each sub-populator CLI must
    implement functions ``make_parser`` and ``main`` to generate the arguments and dispatch them to the corresponding
    caller. The ``main`` function should accept a sequence of string arguments, which can be passed to the parser
    obtained from ``make_parser``.

    An optional ``runner`` can also be defined in each populator module. If provided, the namespace arguments that have
    already been parsed to resolve the populator to run will be used directly, avoiding parsing arguments twice.
    """
    parser = argparse.ArgumentParser(prog="run", description="STACpopulator implementation runner.")
    subparsers = parser.add_subparsers(title="populator", dest="populator", description="Implementation to run.")
    populators_impl = "implementations"
    populators_dir = os.path.join(os.path.dirname(__file__), populators_impl)
    populator_mods = glob.glob(f"{populators_dir}/**/[!__init__]*.py", recursive=True)  # potential candidate scripts
    for populator_path in sorted(populator_mods):
        populator_script = populator_path.split(populators_dir, 1)[1][1:]
        populator_py_mod = os.path.splitext(populator_script)[0].replace(os.sep, ".")
        populator_name, pop_mod_file = populator_py_mod.rsplit(".", 1)
        populator_root = f"STACpopulator.{populators_impl}.{populator_name}"
        pop_mod_file_loc = f"{populator_root}.{pop_mod_file}"
        populator_module = importlib.import_module(pop_mod_file_loc, populator_root)
        parser_maker: Callable[[], argparse.ArgumentParser] = getattr(populator_module, "make_parser", None)
        populator_runner = getattr(populator_module, "runner", None)  # optional, call main directly if not available
        populator_caller = getattr(populator_module, "main", None)
        if callable(parser_maker) and callable(populator_caller):
            populator_parser = parser_maker()
            populator_prog = f"{parent} {parser.prog} {populator_name}"
            subparsers.add_parser(
                populator_name,
                prog=populator_prog, parents=[populator_parser], formatter_class=populator_parser.formatter_class,
                add_help=False,  # add help disabled otherwise conflicts with this main populator help
                help=populator_parser.description, description=populator_parser.description,
                usage=populator_parser.usage,
            )
            POPULATORS[populator_name] = {
                "name": populator_name,
                "caller": populator_caller,
                "parser": populator_parser,
                "runner": populator_runner,
            }
    return parser


def main(*args: str) -> Optional[int]:
    parser = make_main_parser()
    args = args or sys.argv[1:]  # same as was parse args does, but we must provide them to subparser
    ns = parser.parse_args(args=args)  # if 'command' or 'populator' unknown, auto prints the help message with exit(2)
    params = vars(ns)
    populator_cmd = params.pop("command")
    if not populator_cmd:
        parser.print_help()
        return 0
    result = None
    if populator_cmd == "run":
        populator_name = params.pop("populator")
        if not populator_name:
            parser.print_help()
            return 0
        populator_args = args[2:]  # skip [command] [populator]
        populator_caller = POPULATORS[populator_name]["caller"]
        populator_runner = POPULATORS[populator_name]["runner"]
        if populator_runner:
            result = populator_runner(ns)
        else:
            result = populator_caller(*populator_args)
    return 0 if result is None else result


if __name__ == "__main__":
    sys.exit(main())
