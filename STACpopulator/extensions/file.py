import hashlib
from pathlib import Path
from typing import Optional

import pystac
import requests
from netCDF4 import Dataset

from STACpopulator.extensions.base import Helper


class FileHelper(Helper):
    """Helper to handle file info from elements of types Asset and Link."""

    def __init__(self, href: str, download_dir: str = "temp_files") -> None:
        """Initialize the FileHelper object."""
        self.href = href
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.local_path = self.download_dir / Path(href).name
        self.download_file()  # Download the file

        # Compute properties
        self.size = self.local_path.stat().st_size
        self.checksum = self.calculate_checksum()
        #     self.header_size = self.get_netcdf_header_size(self.local_path)
        self.byte_order = self.find_byte_order()

    def download_file(self) -> None:
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
