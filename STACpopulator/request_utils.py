import argparse
from http import cookiejar

import requests
from requests.auth import AuthBase, HTTPBasicAuth, HTTPDigestAuth, HTTPProxyAuth
from requests.sessions import Session


class HTTPBearerTokenAuth(AuthBase):
    """Authorizer class for HTTP Bearer Tokens."""
    
    def __init__(self, token: str) -> None:
        self._token = token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Call this authorizer."""
        r.headers["Authorization"] = f"Bearer {self._token}"
        return r


def add_request_options(parser: argparse.ArgumentParser) -> None:
    """Add arguments to a parser to allow update of a request session definition used across a populator procedure."""
    parser.add_argument(
        "--no-verify",
        "--no-ssl",
        "--no-ssl-verify",
        dest="verify",
        action="store_false",
        help="Disable SSL verification (not recommended unless for development/test servers).",
    )
    parser.add_argument("--cert", type=argparse.FileType(), help="Path to a certificate file to use.")
    parser.add_argument(
        "--auth-handler",
        choices=["basic", "digest", "bearer", "proxy", "cookie"],
        help="Authentication strategy to employ for the requests session.",
    )
    parser.add_argument(
        "--auth-identity",
        help="Bearer token, cookie-jar file or proxy/digest/basic username:password for selected authorization handler.",
    )


def apply_request_options(session: Session, namespace: argparse.Namespace) -> None:
    """Apply the relevant request session options from parsed input arguments."""
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
        session.cookies = cookiejar.MozillaCookieJar(namespace.auth_identity)
        session.cookies.load(namespace.auth_identity)
