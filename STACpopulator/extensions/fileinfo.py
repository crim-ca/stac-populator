import json
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, Union, cast

import pystac
from pystac.extensions.base import ExtensionManagementMixin, PropertiesExtension

T = TypeVar("T", pystac.Asset, pystac.Link)
SCHEMA_URI = "https://stac-extensions.github.io/file/v2.1.0/schema.json"


@dataclass
class FileInfo:
    """File Info Properties."""

    size: Optional[int] = None
    checksum: Optional[str] = None
    header_size: Optional[int] = None
    byte_order: Optional[str] = None
    local_path: Optional[str] = None


class FileInfoExtension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[Union[pystac.Asset, pystac.Link]],
):
    """FileInfoExtension class."""

    def apply(self, properties: Union[FileInfo, dict[str, any]]) -> None:
        """Apply File Info Extension to the extended STAC Item or Asset."""
        if isinstance(properties, dict):
            properties = FileInfo(**properties)
        data_json = json.loads(properties.model_dump_json(by_alias=True))
        for prop, val in data_json.items():
            self._set_property(prop, val)

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> "FileInfoExtension[T]":
        """Extend the given STAC Object with properties from the :stac-ext:`FileInfo Extension <cf>`.

        This extension can be applied to instances of :class:`~pystac.Asset` or
        :class:`~pystac.Link`.

        Raises
        ------
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        cls.ensure_has_extension(obj, add_if_missing)
        return cast(FileInfoExtension[T], cls(obj))

    @classmethod
    def get_schema_uri(cls) -> str:
        """Return this extension's schema URI."""
        return SCHEMA_URI
