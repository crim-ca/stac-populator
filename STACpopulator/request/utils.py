import argparse
import logging

from requests.sessions import Session

from STACpopulator.auth.handlers import AuthHandler
from STACpopulator.auth.validators import ValidateAuthHandlerAction, ValidateHeaderAction, ValidateMethodAction

LOGGER = logging.getLogger(__name__)


def add_request_options(parser: argparse.ArgumentParser) -> None:
    """Add arguments to a parser to allow update of a request session definition used across a populator procedure."""
    auth_handlers = ", ".join(ValidateAuthHandlerAction.DEFAULT_HANDLER_ALIASES.keys())

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
        metavar="AUTH_HANDLER",
        action=ValidateAuthHandlerAction,
        help=(
            "Authentication handler to use. "
            f"Built-in options: {auth_handlers}. "
            "For custom handlers, use: 'path/to/script.py:ClassName' or 'module:ClassName'."
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
        default="GET",
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
            "`Header-Name: value`. Header names are case-insensitive; single or double quotes may be used to delimit the value; "
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

    # Extract auth options from namespace to prevent no attribute errors
    auth_handler = getattr(ns, "auth_handler", None)
    auth_identity = getattr(ns, "auth_identity", None)
    auth_url = getattr(ns, "auth_url", None)
    auth_method = getattr(ns, "auth_method", None)
    auth_headers = getattr(ns, "auth_headers", None)
    auth_token = getattr(ns, "auth_token", None)

    # Check if any auth options are provided without an auth_handler.
    # `auth_method` has a default value, so we don't check it here.
    if any([auth_identity, auth_url, auth_headers, auth_token]) and not auth_handler:
        raise ValueError(
            "auth_handler must be specified when using authentication options "
            "(--auth-identity, --auth-url, --auth-method, --auth-header, --auth-token)"
        )

    if not auth_handler:
        return

    session.auth = AuthHandler.from_data(
        auth_handler=auth_handler,
        auth_identity=auth_identity,
        auth_url=auth_url,
        auth_method=auth_method,
        auth_headers=auth_headers,
        auth_token=auth_token,
    )
