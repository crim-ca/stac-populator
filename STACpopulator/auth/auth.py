import abc
import logging
from http import HTTPStatus
from typing import Any, Optional, Union

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
from STACpopulator.auth.utils import fully_qualified_name, get_header, request_extra
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
        resp = request_extra(self.method, self.url, headers=auth_headers)
        if resp.status_code != HTTPStatus.OK:
            return None
        return self.get_token_from_response(resp)

    def get_token_from_response(self, response: Response) -> Optional[str]:
        """Extract the authorization token from a valid authentication response."""
        ctype = get_header("Content-Type", response.headers)
        auth_token = None
        if ContentType.APP_JSON in ctype:
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
        """Parse token to a form that can be included in a request header.

        Parameters
        ----------
            token (str):
                Authorization token.

        Returns
        -------
            str:
                the token string as is.
        """
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
        """Parse token to a form that can be included in a request header.

        Returns the token string as is if it is a string. Otherwise, if the token is a mapping, where keys are cookie
        names and values are cookie values, convert the cookie representation to a string that can be accepted as the
        value of the "Cookie" header.
        """
        if isinstance(token, str):
            return token
        cookie_dict = CaseInsensitiveDict(token)
        return "; ".join(f"{key}={val}" for key, val in cookie_dict.items())

    def auth_header(self, token: str) -> AnyHeadersContainer:
        """Header definition for cookie-based authentication."""
        return {"Cookie": token}
