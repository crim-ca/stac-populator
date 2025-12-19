import argparse
import re
from typing import Any, Optional, Sequence, Union

from requests.auth import AuthBase

from STACpopulator.auth.handlers import AuthHandler
from STACpopulator.auth.utils import fully_qualified_name, import_target


class ValidateAuthHandlerAction(argparse.Action):
    """Action that will validate that the input argument references an authentication handler that can be resolved."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        auth_handler_ref: Optional[str],
        option_string: Optional[str] = None,
    ) -> None:
        """Validate the referenced authentication handler implementation."""
        if not (auth_handler_ref and isinstance(auth_handler_ref, str)):
            return None
        auth_handler = import_target(auth_handler_ref)
        if not auth_handler:
            error = f"Could not resolve class reference to specified Authentication Handler: [{auth_handler_ref}]."
            raise argparse.ArgumentError(self, error)
        auth_handler_name = fully_qualified_name(auth_handler)
        if not issubclass(auth_handler, (AuthHandler, AuthBase)):
            error = (
                f"Resolved Authentication Handler [{auth_handler_name}] is "
                "not of appropriate sub-type: oneOf[AuthHandler, AuthBase]."
            )
            raise argparse.ArgumentError(self, error)
        setattr(namespace, self.dest, auth_handler)


class ValidateMethodAction(argparse.Action):
    """Action that will validate that the input argument one of the accepted HTTP methods."""

    methods = ["GET", "HEAD", "POST", "PUT", "DELETE"]

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Optional[Union[str, Sequence[Any]]],
        option_string: Optional[str] = None,
    ) -> None:
        """Validate the method value."""
        if values not in self.methods:
            allow = ", ".join(self.methods)
            error = f"Value '{values}' is not a valid HTTP method, must be one of [{allow}]."
            raise argparse.ArgumentError(self, error)
        setattr(namespace, self.dest, values)


class ValidateHeaderAction(argparse._AppendAction):  # noqa
    """Action that will validate that the input argument is a correctly formed HTTP header name.

    Each header should be provided as a separate option using format:

    .. code-block:: text
        Header-Name: Header-Value
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Optional[Union[str, Sequence[Any]]],
        option_string: Optional[str] = None,
    ) -> None:
        """Validate the header value."""
        # items are received one by one with successive calls to this method on each matched (repeated) option
        # gradually convert them to header representation
        super(ValidateHeaderAction, self).__call__(parser, namespace, values, option_string)
        values = getattr(namespace, self.dest, [])
        headers = []
        if values:
            for val in values:
                if isinstance(val, tuple):  # skip already processed
                    headers.append(val)
                    continue
                if isinstance(val, list) and len(val) == 1:  # if nargs=1
                    val = val[0]
                hdr = re.match(r"^\s*(?P<name>[\w+\-]+)\s*\:\s*(?P<value>.*)$", val)
                if not hdr:
                    error = f"Invalid header '{val}' is missing name or value separated by ':'."
                    raise argparse.ArgumentError(self, error)
                if len(hdr["value"]) >= 2 and hdr["value"][0] in ["\"'"] and hdr["value"][-1] in ["\"'"]:
                    value = hdr["value"][1:-1]
                else:
                    value = hdr["value"]
                name = hdr["name"].replace("_", "-")
                headers.append((name, value))
        setattr(namespace, self.dest, headers)
