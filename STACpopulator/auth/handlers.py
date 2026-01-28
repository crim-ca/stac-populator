from __future__ import annotations

import abc
import inspect
import logging
from http import cookiejar
from typing import Any, Optional, Type

from requests import PreparedRequest, Response
from requests.auth import AuthBase, HTTPBasicAuth, HTTPDigestAuth, HTTPProxyAuth
from requests.structures import CaseInsensitiveDict

from STACpopulator.auth.utils import fully_qualified_name, make_request
from STACpopulator.exceptions import AuthenticationError
from STACpopulator.request.typedefs import (
    APP_JSON,
    AnyHeadersContainer,
    AnyRequestType,
    CookiesType,
    RequestMethod,
)

LOGGER = logging.getLogger(__name__)


class AuthHandler(AuthBase):
    """Authentication handler class."""

    url: Optional[str]
    method: RequestMethod
    headers: AnyHeadersContainer
    identity: Optional[str]
    password: Optional[str]

    def __init__(
        self,
        identity: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        method: RequestMethod = "GET",
        headers: Optional[AnyHeadersContainer] = None,
    ) -> None:
        self.identity = identity
        self.password = password
        self.url = url
        self.method = method if method is not None else "GET"
        self.headers = headers if headers is not None else {}

    @abc.abstractmethod
    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        """Call method to perform inline authentication retrieval prior to sending the request."""
        raise NotImplementedError

    @staticmethod
    def from_data(
        auth_handler: Optional[Type[AuthHandler]] = None,
        auth_identity: Optional[str] = None,
        auth_url: Optional[str] = None,
        auth_method: Optional[str] = None,
        auth_headers: Optional[dict] = None,
        auth_token: Optional[str] = None,
    ) -> Optional[AuthHandler]:
        """Parse arguments that define an authentication handler.

        Args:
            auth_handler: The authentication handler class to instantiate.
            auth_identity: Identity string, optionally containing password as "user:pass".
            auth_url: URL for authentication.
            auth_method: Authentication method (HTTP verb).
            auth_headers: Additional headers for authentication.
            auth_token: Authentication token.

        Returns
        -------
            An instantiated `AuthHandler`, or None if `auth_handler` is invalid.
        """
        if not (auth_handler and issubclass(auth_handler, (AuthHandler, AuthBase))):
            return None

        auth_password = None
        if auth_identity and ":" in auth_identity:
            auth_identity, auth_password = auth_identity.split(":", 1)

        auth_headers = auth_headers or {}

        auth_handler_sign = inspect.signature(auth_handler)
        auth_opts = [
            ("username", auth_identity),
            ("identity", auth_identity),
            ("password", auth_password),
            ("url", auth_url),
            ("method", auth_method),
            ("headers", CaseInsensitiveDict(auth_headers)),
            ("token", auth_token),
        ]

        if not auth_handler_sign.parameters:
            auth_handler_obj = auth_handler()
            for auth_param, auth_option in auth_opts:
                if auth_option and hasattr(auth_handler_obj, auth_param):
                    setattr(auth_handler_obj, auth_param, auth_option)
        else:
            auth_params = list(auth_handler_sign.parameters)
            auth_kwargs = {opt: val for opt, val in auth_opts if opt in auth_params}

            # allow partial match of required parameters by name to support custom implementations
            # (e.g.: 'MagpieAuth' using 'magpie_url' instead of plain 'url')
            for param_name, param in auth_handler_sign.parameters.items():
                if param.kind not in [param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD]:
                    continue
                if param_name not in auth_kwargs:
                    for opt, val in auth_opts:
                        if param_name.endswith(opt):
                            LOGGER.debug("Using authentication partial match: [%s] -> [%s]", opt, param_name)
                            auth_kwargs[param_name] = val
                            break
            LOGGER.debug("Using authentication parameters: %s", auth_kwargs)
            auth_handler_obj = auth_handler(**auth_kwargs)
        LOGGER.info(
            "Will use specified Authentication Handler [%s] with provided options.",
            fully_qualified_name(auth_handler),
        )
        return auth_handler_obj


class BasicAuthHandler(AuthHandler, HTTPBasicAuth):
    """Basic authentication handler class.

    Adds the `Authorization` header formed from basic authentication encoding of username and password to the request.

    Authentication URL and method are not needed for this handler.
    """

    def __init__(self, username: str, password: str, **kwargs) -> None:
        AuthHandler.__init__(self, identity=username, password=password, **kwargs)
        HTTPBasicAuth.__init__(self, username=username, password=password)

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        """Call method to perform authentication prior to sending the request."""
        return HTTPBasicAuth.__call__(self, r)


class DigestAuthHandler(AuthHandler, HTTPDigestAuth):
    """Digest authentication handler class."""

    def __init__(self, username: str, password: str, **kwargs) -> None:
        AuthHandler.__init__(self, identity=username, password=password, **kwargs)
        HTTPDigestAuth.__init__(self, username=username, password=password)

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        """Call method to perform authentication prior to sending the request."""
        return HTTPDigestAuth.__call__(self, r)


class ProxyAuthHandler(AuthHandler, HTTPProxyAuth):
    """Proxy authentication handler class."""

    def __init__(self, username: str, password: str, **kwargs) -> None:
        AuthHandler.__init__(self, identity=username, password=password, **kwargs)
        HTTPProxyAuth.__init__(self, username=username, password=password)

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        """Call method to perform authentication prior to sending the request."""
        return HTTPProxyAuth.__call__(self, r)


class CookieJarAuthHandler(AuthHandler):
    """Cookie jar authentication handler class."""

    def __init__(self, identity: str, **kwargs) -> None:
        AuthHandler.__init__(self, identity=identity, **kwargs)
        self.cookiefile = identity
        self._cookiejar = None

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        """Call method loading cookie jar prior to sending the request."""
        # Lazy-load cookie jar
        if self._cookiejar is None:
            jar = cookiejar.MozillaCookieJar(self.cookie_file)
            jar.load(ignore_discard=True, ignore_expires=True)
            self._cookiejar = jar

        r._cookies = self._cookiejar
        return r


class RequestAuthHandler(AuthHandler):
    """Base class to send a request in order to retrieve an authorization token."""

    def __init__(
        self,
        identity: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        method: RequestMethod = "GET",
        headers: Optional[AnyHeadersContainer] = None,
        token: Optional[str] = None,
    ) -> None:
        AuthHandler.__init__(
            self,
            identity=identity,
            password=password,
            url=url,
            method=method,
            headers=headers,
        )
        self.token = token
        self._common_token_names = ["auth", "access_token", "token"]

        if not self.token and not self.url:
            raise AuthenticationError("Either the token or the URL to retrieve it must be provided to the handler.")

    @property
    def auth_token_name(self) -> Optional[str]:
        """Override token name to retrieve in response authentication handler implementation.

        Defaults to `None` and auth handler then looks amongst common names: [`auth`, `access_token`, `token`]
        """
        return None

    @abc.abstractmethod
    def auth_header(self, token: str) -> AnyHeadersContainer:
        """Get the header definition with the provided authorization token."""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def parse_token(token: Any) -> str:
        """Parse token to a format that can be included in a request header."""
        raise NotImplementedError

    def authenticate(self) -> Optional[str]:
        """Launch an authentication request to retrieve the authorization token."""
        auth_headers = {"Accept": APP_JSON}
        auth_headers.update(self.headers)
        res = make_request(self.method, self.url, headers=auth_headers)
        if not res.ok:
            return None
        return self.get_token_from_response(res)

    def get_token_from_response(self, response: Response) -> Optional[str]:
        """Extract the authorization token from a valid authentication response."""
        content_type = response.headers.get("Content-Type")
        if not content_type == APP_JSON:
            return None

        body = response.json()
        if self.auth_token_name:
            auth_token = body.get(self.auth_token_name)
        else:
            auth_token = next(
                (body[name] for name in self._common_token_names if name in body),
                None,
            )
        return auth_token

    def __call__(self, request: AnyRequestType) -> AnyRequestType:
        """Call method handling authentication and request forward."""
        auth_token = self.authenticate() if self.token is None and self.url else self.token
        if not auth_token:
            LOGGER.warning(
                "Expected authorization token could not be retrieved from URL: [%s] in [%s]",
                self.url,
                fully_qualified_name(self),
            )
        else:
            auth_token = self.parse_token(auth_token)
            auth_header = self.auth_header(auth_token)
            request.headers.update(auth_header)
        return request


class BearerAuthHandler(RequestAuthHandler):
    """Bearer authentication handler class.

    Adds the ``Authorization`` header formed of the authentication bearer token from the underlying request.
    """

    @staticmethod
    def parse_token(token: str) -> str:
        """Parse token to a form that can be included in a request header."""
        return token

    def auth_header(self, token: str) -> AnyHeadersContainer:
        """Header definition for bearer token-based authentication."""
        return {"Authorization": f"Bearer {token}"}


class CookieAuthHandler(RequestAuthHandler):
    """Cookie-based authentication handler class.

    Adds the ``Cookie`` header formed from the authentication bearer token from the underlying request.
    """

    def __init__(
        self,
        identity: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        method: RequestMethod = "GET",
        headers: Optional[AnyHeadersContainer] = None,
        token: Optional[str | CookiesType] = None,
    ) -> None:
        super().__init__(
            identity=identity,
            password=password,
            url=url,
            method=method,
            headers=headers,
            token=token,
        )

    @staticmethod
    def parse_token(token: str | CookiesType) -> str:
        """Parse token to a form that can be included in a request `Cookie` header.

        Returns the token string as is if it's a string. Otherwise, if the token is a mapping where keys are cookie
        names and values are cookie values, converts the cookie to a `key=val;...` string that can be accepted as the
        value of the "Cookie" header.
        """
        if isinstance(token, str):
            return token
        cookie_dict = CaseInsensitiveDict(token)
        return "; ".join(f"{key}={val}" for key, val in cookie_dict.items())

    def auth_header(self, token: str) -> AnyHeadersContainer:
        """Header definition for cookie-based authentication."""
        return {"Cookie": token}
