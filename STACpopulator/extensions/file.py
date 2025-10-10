import functools
import hashlib
import io
from typing import Dict, TypeVar

import pystac
import requests
from pystac.extensions.file import FileExtension

from STACpopulator.extensions.base import ExtensionHelper

T = TypeVar("T", pystac.Asset, pystac.Link)


class FileHelper(ExtensionHelper):
    """Helper to handle file info from elements of types Asset and Link."""

    access_urls: Dict[str, str]
    _local_file = None
    _header_size = None

    def apply(self, item: pystac.Item, add_if_missing: bool = True) -> T:
        """Apply the FileExtension to an asset."""
        if self._local_file is None:
            self.load_file()

        # FIXME: This extension is applicable to Assets and Links.
        # Right now it is only applied to the HTTPServer asset to avoid
        # too much load/latence when running the populator
        asset = item.assets["HTTPServer"]
        file_ext = FileExtension.ext(asset, add_if_missing=add_if_missing)
        file_ext.apply(
            byte_order=None,  # NOTE: Appear to available for each variable. Not sure what would be the value for the whole file.
            checksum=self.checksum,
            header_size=self.header_size,
            size=self.size,
            values=None,  # NOTE: deprecated
            local_path=None,  # NOTE: might not be relevant
        )

    def load_file(self) -> None:
        """Download the current file into temporary directory."""
        if self._local_file is not None:
            return
        response = requests.get(self.access_urls["HTTPServer"], stream=True)
        response.raise_for_status()

        # Read the first 64 KB for header/metadata (NetCDF4/HDF5 header)
        head_chunk = response.raw.read(64 * 1024)
        self._header_size = len(head_chunk)

        # Initialize in-memory buffer with header
        buffer = io.BytesIO(head_chunk)

        # Read the rest of the stream and append to buffer while counting
        for chunk in response.iter_content(chunk_size=8192):
            buffer.write(chunk)

        # Store all data in memory
        self._local_file = buffer.getvalue()

    @functools.cached_property
    def size(self) -> int:
        """Return file size in bytes."""
        return len(self._local_file)

    @functools.cached_property
    def checksum(self) -> str:
        """Return file sha256 checksum."""
        return hashlib.sha256(self._local_file).hexdigest()

    @functools.cached_property
    def header_size(self) -> int:
        """Return the header size of the netCDF (.nc) file in bytes."""
        return self._header_size
