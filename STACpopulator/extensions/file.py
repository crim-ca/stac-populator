"""FileHelper module."""

import functools
from typing import Dict, Optional, TypeVar

import pystac
import requests
from pystac.extensions.file import FileExtension
from requests import Session

from STACpopulator.extensions.base import ExtensionHelper

# Constants
T = TypeVar("T", pystac.Asset, pystac.Link)
HTTP_SERVER_ASSET_KEY = "HTTPServer"
OPEN_DAP_ASSET_KEY = "OpenDAP"


class FileHelper(ExtensionHelper):
    """Helper to handle file info from elements of types Asset and Link."""

    access_urls: Dict[str, str]
    _session: Optional[Session] = None

    def __init__(self, access_urls: dict[str, str], session: Optional[Session] = None) -> None:
        """Initialize the file helper.

        Parameters
        ----------
        access_urls : dict
            Dictionary of catalog access URLs.
        session : requests.Session, optional
            Requests session object to use for HTTP requests. Defaults to requests.Session().
        """
        super().__init__(access_urls=access_urls, _session=session)

    def apply(self, item: pystac.Item, add_if_missing: bool = True) -> T:
        """Apply the FileExtension to an asset."""
        # FIXME: This extension is applicable to Assets and Links.
        # Currently only applied to the HTTPServer asset to avoid heavy load during populator run
        asset = item.assets[HTTP_SERVER_ASSET_KEY]
        file_ext = FileExtension.ext(asset, add_if_missing=add_if_missing)
        file_ext.apply(
            size=self.size,
            byte_order=None,  # NOTE: Appears to be variable-related. Unclear what would be the value for the whole file.
            header_size=None,  # NOTE: No utility yet available. Might not be relevant.
            checksum=None,  # NOTE: Should be made available in the metadata on THREDDS catalog
            values=None,  # NOTE: Deprecated field
            local_path=None,  # NOTE: Seems to be irrelevant
        )

    @property
    def session(self) -> Session:
        """Get requests session."""
        if self._session is None:
            # Initialize only on first call to allow setting value post init.
            self._session = requests.Session()
        return self._session

    @session.setter
    def session(self, value: Session) -> None:
        """Set requests session."""
        self._session = value

    @functools.cached_property
    def size(self) -> int:
        """Return file size in bytes."""
        if HTTP_SERVER_ASSET_KEY not in self.access_urls:
            return 0
        res = self.session.head(self.access_urls[HTTP_SERVER_ASSET_KEY])
        res.raise_for_status()
        return int(res.headers.get("Content-Length", None))
