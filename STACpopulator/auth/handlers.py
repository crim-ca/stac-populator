from __future__ import annotations

import abc
import inspect
import logging
from http import HTTPStatus
from typing import Any, Dict, Optional, Type, Union

from requests import Response
from requests.auth import AuthBase, HTTPBasicAuth
from requests.structures import CaseInsensitiveDict

from STACpopulator.auth.typedefs import (
    AnyHeadersContainer,
    AnyRequestMethod,
    AnyRequestType,
    ContentType,
    CookiesType,
)
from STACpopulator.auth.utils import fully_qualified_name, make_request
from STACpopulator.exceptions import AuthenticationError

LOGGER = logging.getLogger("cli.auth")


class AuthHandler(AuthBase):
    """Authentication handler class."""

    url: Optional[str] = None
    method: AnyRequestMethod = "GET"
    headers: Optional[AnyHeadersContainer] = {}
    identity: Optional[str] = None
    password: Optional[str] = None  # nosec

    def __init__(
        self,
        identity: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        method: AnyRequestMethod = "GET",
        headers: Optional[AnyHeadersContainer] = None,
    ) -> None:
        if identity is not None:
            self.identity = identity
        if password is not None:
            self.password = password
        if url is not None:
            self.url = url
        if method is not None:
            self.method = method
        if headers:
            self.headers = headers

    @abc.abstractmethod
    def __call__(self, request: AnyRequestType) -> AnyRequestType:
        """Call method to perform inline authentication retrieval prior to sending the request."""
        raise NotImplementedError

    @staticmethod
    def from_data(
        kwargs: Dict[str, Optional[Union[Type[AuthHandler], str]]],
    ) -> Optional[AuthHandler]:
        """Parse arguments that can define an authentication handler and remove them from dictionary for following calls."""
        auth_handler = kwargs.pop("auth_handler", None)
        auth_identity = kwargs.pop("auth_identity", None)
        auth_identity, auth_password = (auth_identity.split(":", 1) if auth_identity else None), None
        auth_url = kwargs.pop("auth_url", None)
        auth_method = kwargs.pop("auth_method", None)
        auth_headers = kwargs.pop("auth_headers", {})
        auth_token = kwargs.pop("auth_token", None)

        if not (auth_handler and issubclass(auth_handler, (AuthHandler, AuthBase))):
            return None

        auth_handler_name = fully_qualified_name(auth_handler)
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
        if len(auth_handler_sign.parameters) == 0:
            auth_handler = auth_handler()
            for auth_param, auth_option in auth_opts:
                if auth_option and hasattr(auth_handler, auth_param):
                    setattr(auth_handler, auth_param, auth_option)
        else:
            auth_params = list(auth_handler_sign.parameters)
            auth_kwargs = {opt: val for opt, val in auth_opts if opt in auth_params}
            # allow partial match of required parameters by name to better support custom implementations
            # (e.g.: 'MagpieAuth' using 'magpie_url' instead of plain 'url')
            for param_name, param in auth_handler_sign.parameters.items():
                if param.kind not in [
                    param.POSITIONAL_ONLY,
                    param.POSITIONAL_OR_KEYWORD,
                ]:
                    continue
                if param_name not in auth_kwargs:
                    for opt, val in auth_opts:
                        if param_name.endswith(opt):
                            LOGGER.debug(
                                "Using authentication partial match: [%s] -> [%s]",
                                opt,
                                param_name,
                            )
                            auth_kwargs[param_name] = val
                            break
            LOGGER.debug("Using authentication parameters: %s", auth_kwargs)
            auth_handler = auth_handler(**auth_kwargs)
        LOGGER.info(
            "Will use specified Authentication Handler [%s] with provided options.",
            auth_handler_name,
        )
        return auth_handler


class BasicAuthHandler(AuthHandler, HTTPBasicAuth):
    """Basic authentication handler class.

    Adds the `Authorization` header formed from basic authentication encoding of username and password to the request.

    Authentication URL and method are not needed for this handler.
    """

    def __init__(self, username: str, password: str, **kwargs) -> None:
        AuthHandler.__init__(self, identity=username, password=password, **kwargs)
        HTTPBasicAuth.__init__(self, username=username, password=password)

    @property
    def username(self) -> str:
        """Auth username."""
        return self.identity

    @username.setter
    def username(self, username: str) -> None:
        self.identity = username

    def __call__(self, request: AnyRequestType) -> AnyRequestType:
        """Call method for basic authentication handler."""
        return HTTPBasicAuth.__call__(self, request)


class RequestAuthHandler(AuthHandler, HTTPBasicAuth):
    """Base class to send a request in order to retrieve an authorization token."""

    def __init__(
        self,
        identity: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        method: AnyRequestMethod = "GET",
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
        HTTPBasicAuth.__init__(self, username=identity, password=password)
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
        auth_headers = {"Accept": ContentType.APP_JSON}
        auth_headers.update(self.headers)
        resp = make_request(self.method, self.url, headers=auth_headers)
        if resp.status_code != HTTPStatus.OK:
            return None
        return self.get_token_from_response(resp)

    def get_token_from_response(self, response: Response) -> Optional[str]:
        """Extract the authorization token from a valid authentication response."""
        content_type = response.headers.get("Content-Type")
        if not content_type == ContentType.APP_JSON:
            return None

        body = response.json()
        if self.auth_token_name:
            auth_token = body.get(self.auth_token_name)
        else:
            auth_token = next(
                (body[name] for name in self._common_token_names if name in body),
                default=None,
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
        method: AnyRequestMethod = "GET",
        headers: Optional[AnyHeadersContainer] = None,
        token: Optional[Union[str, CookiesType]] = None,
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
    def parse_token(token: Union[str, CookiesType]) -> str:
        """Parse token to a form that can be included in a request `Cookie` header.

        Returns the token string as is if it is a string. Otherwise, if the token is a mapping where keys are cookie
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
