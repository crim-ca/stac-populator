import argparse
import logging

from requests.sessions import Session

from STACpopulator.auth.handlers import AuthHandler, BasicAuthHandler, BearerAuthHandler, CookieAuthHandler
from STACpopulator.auth.utils import fully_qualified_name
from STACpopulator.auth.validators import ValidateAuthHandlerAction, ValidateHeaderAction, ValidateMethodAction

LOGGER = logging.getLogger(__name__)


def add_request_options(parser: argparse.ArgumentParser) -> None:
    """Add arguments to a parser to allow update of a request session definition used across a populator procedure."""
    auth_handlers = " | ".join(
        [f"{fully_qualified_name(handler)}" for handler in [BasicAuthHandler, BearerAuthHandler, CookieAuthHandler]]
    )

    parser.add_argument("--cert", type=argparse.FileType(), help="Path to a certificate file to use.")
    parser.add_argument(
        "--no-verify",
        "--no-ssl",
        "--no-ssl-verify",
        dest="verify",
        action="store_false",
        help="Disable SSL verification (not recommended unless for development/test servers).",
    )
    parser.add_argument(
        "-c",
        "--auth-handler",
        dest="auth_handler",
        metavar="AUTH_HANDLER_CLASS",
        action=ValidateAuthHandlerAction,
        help=(
            "Script or module path reference to a class that handles inline request authentication."
            "The expected format is path/to/script.py:module.AuthHandlerClass or installed.module.AuthHandlerClass."
            f"Following built-in implementations are available: {auth_handlers}."
            "Custom implementations may be provided for more advanced use cases."
        ),
    )
    parser.add_argument(
        "-i",
        "--auth-identity",
        dest="auth_identity",
        metavar="USR:PWD",
        help="Authentication credentials (username:password) to be passed down to the specified Authentication Handler.",
    )
    parser.add_argument(
        "-u",
        "--auth-url",
        dest="auth_url",
        help="Authentication URL to be passed down to the specified Authentication Handler.",
    )
    parser.add_argument(
        "-m",
        "--auth-method",
        dest="auth_method",
        metavar="HTTP_METHOD",
        action=ValidateMethodAction,
        choices=ValidateMethodAction.methods,
        type=str.upper,
        default=AuthHandler.method,
        help=(
            "Authentication HTTP request method to be passed down to the specified Authentication Handler "
            "(default: %(default)s, case-insensitive)."
        ),
    )
    parser.add_argument(
        "-H",
        "--auth-header",
        action=ValidateHeaderAction,
        nargs=1,
        dest="auth_headers",
        metavar="HEADER",
        help=(
            "Additional HTTP headers to include when sending requests via the authentication handler. "
            "This option may be specified multiple times; each value must be formatted as "
            "`Header-Name: value`. Header names are case-insensitive; single or double quotes may be used to delimit the value;"
            "surrounding spaces are trimmed."
        ),
    )
    parser.add_argument(
        "-t",
        "--auth-token",
        dest="auth_token",
        metavar="TOKEN",
        help=(
            "Token to be added directly to the request headers. If this is specified, the authenticator will not make "
            "an additional authentication request in order to obtain a token. The token specified here will be used "
            "instead."
        ),
    )


def apply_request_options(session: Session, ns: argparse.Namespace) -> None:
    """Apply the relevant request session options from parsed input arguments."""
    session.verify = ns.verify
    session.cert = ns.cert
    if not ns.auth_handler:
        return

    kwargs = vars(ns)
    session.auth = AuthHandler.from_data(kwargs)
