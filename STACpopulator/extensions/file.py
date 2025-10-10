import hashlib
from pathlib import Path
from typing import Optional, TypeVar

import pystac
import requests
from netCDF4 import Dataset
from pystac.extensions.file import FileExtension

from STACpopulator.extensions.base import ExtensionHelper

T = TypeVar("T", pystac.Asset, pystac.Link)


class FileHelper(ExtensionHelper):
    """Helper to handle file info from elements of types Asset and Link."""

    def __init__(self, href: str) -> None:
        """Initialize the FileHelper object."""
        self.href = href
        self.local_file = None

    def apply(self, asset: T, add_if_missing: bool = True) -> T:
        """Apply the FileExtension to an asset."""
        self.load_file()
        file_ext = FileExtension.ext(asset, add_if_missing=add_if_missing)
        file_ext.apply(
            byte_order=self.byte_order,
            checksum=self.checksum,  # FIXME: Displayed as n/a on browser
            header_size=0,  # FIXME: clarify expected value here
            size=self.size,
            values=None,  # NOTE: deprecated
            local_path=None,  # FIXME: clarify expected value here
        )

    def load_file(self) -> None:
        """Download the current file into temporary directory."""
        if self.local_path.exists():
            return
        r = requests.get(self.href, stream=True)
        r.raise_for_status()
        with open(self.local_path, "wb") as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)

    def calculate_checksum(self) -> str:
        """Return file md5 checksum value."""
        h = hashlib.md5()
        with open(self.local_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    def find_byte_order(self) -> Optional[pystac.extensions.file.ByteOrder]:
        """Detect byte order based on file header content."""
        # TODO: Check TIFF header. To be double-checked
        with open(self.local_path, "rb") as f:
            header = f.read(2)
        if header == b"II":
            return "little-endian"
        elif header == b"MM":
            return "big-endian"
        else:
            return None

    def get_netcdf_header_size(self, file_path: Path) -> int:
        """Estimate the header size of a NetCDF (.nc) file in bytes."""
        with Dataset(file_path, "r") as ds:
            variables = ds.variables
            if not variables:
                # No variables → header = full file?
                return file_path.stat().st_size
            # NetCDF-3 classic: header ends at the start of first variable
            first_var = next(iter(variables.values()))
            try:
                offset = first_var._offset
            except AttributeError:
                # NetCDF-4/HDF5: header is less relevant, fallback to 0
                offset = 0
        return offset
