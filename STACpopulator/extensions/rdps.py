"""RPDS Extension Module."""

import json
import os
from datetime import datetime
from typing import (
    Any,
    Generic,
    Iterable,
    Literal,
    MutableMapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
)

import pystac
from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator
from pydantic.fields import FieldInfo
from pystac.extensions import item_assets
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
    S,  # generic pystac.STACObject
    SummariesExtension,
)

from STACpopulator.models import AnyGeometry
from STACpopulator.stac_utils import ServiceType, ncattrs_to_bbox, ncattrs_to_geometry

T = TypeVar("T", pystac.Collection, pystac.Item, pystac.Asset, item_assets.AssetDefinition)

SchemaName = Literal["rdps"]
SCHEMA_URI: str = "STACpopulator/extensions/schemas/rdps/rdps-global-attrs-schema.json"  # FIXME: To be defined
PREFIX = f"{get_args(SchemaName)[0]}:"


def add_ext_prefix(name: str) -> str:
    """Return the given name prefixed with this extension's prefix."""
    return PREFIX + name if "datetime" not in name else name


class RDPSProperties(BaseModel, validate_assignment=True):
    """Data model for RDPS."""

    Conventions: str

    _prefix = "rdps"

    model_config = ConfigDict(alias_generator=add_ext_prefix, populate_by_name=True, extra="ignore")

    @field_validator("version", check_fields=False)
    @classmethod
    def validate_version(cls, v: str, __info: ValidationInfo) -> bool:
        """Return True iff the given version is valid."""
        assert v[0] == "v", "Version string should begin with a lower case 'v'"
        assert v[1:].isdigit(), "All characters in version string, except first, should be digits"
        return v


class RDPSHelper:
    """Helper for RDPS data."""

    def __init__(self, attrs: MutableMapping[str, Any], geometry_model: Type[AnyGeometry]) -> None:
        self.attrs = attrs
        self.rdps_attrs = attrs["attributes"]
        self.cfmeta = attrs["groups"]["CFMetadata"]["attributes"]
        self.geometry_model = geometry_model

    @property
    def uid(self) -> str:
        """Return a unique ID for RDPS data item."""
        item_url = self.attrs["access_urls"]["HTTPServer"]
        item_filename = os.path.basename(item_url)
        _uid, _ = os.path.splitext(item_filename)
        return _uid  # filename without extension

    @property
    def geometry(self) -> AnyGeometry:
        """Return the geometry."""
        return self.geometry_model(**ncattrs_to_geometry(self.attrs))

    @property
    def bbox(self) -> list[float]:
        """Return the bounding box."""
        return ncattrs_to_bbox(self.attrs)

    @property
    def start_datetime(self) -> datetime:
        """Return the beginning of the temporal extent."""
        return self.cfmeta["time_coverage_start"]

    @property
    def end_datetime(self) -> datetime:
        """Return the end of the temporal extent."""
        return self.cfmeta["time_coverage_end"]

    @property
    def properties(self) -> RDPSProperties:
        """Return properties."""
        props = RDPSProperties(**self.rdps_attrs)
        return props

    def stac_item(self) -> "pystac.Item":
        """Return a pystac Item."""
        item = pystac.Item(
            id=self.uid,
            geometry=self.geometry.model_dump(),
            bbox=self.bbox,
            properties={
                "start_datetime": self.start_datetime,
                "end_datetime": self.end_datetime,
            },
            datetime=None,
        )
        return item


class RDPSExtension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[Union[pystac.Asset, pystac.Item, pystac.Collection]],
):
    """Extension for RDPS data."""

    @property
    def name(self) -> SchemaName:
        """Return the schema name."""
        return get_args(SchemaName)[0]

    def apply(
        self,
        properties: Union[RDPSProperties, dict[str, Any]],
    ) -> None:
        """Apply RDPS Extension properties to the extended :class:`~pystac.Item` or :class:`~pystac.Asset`."""
        if isinstance(properties, dict):
            properties = RDPSProperties(**properties)
        data_json = json.loads(properties.model_dump_json(by_alias=True))
        for prop, val in data_json.items():
            self._set_property(prop, val)

    @classmethod
    def get_schema_uri(cls) -> str:
        """Return this extension's schema URI."""
        return SCHEMA_URI

    @classmethod
    def has_extension(cls, obj: S) -> bool:
        """Return True iff the object has an extension for that matches this class' schema URI."""
        # FIXME: this override should be removed once an official and versioned schema is released
        # ignore the original implementation logic for a version regex
        # since in our case, the VERSION_REGEX is not fulfilled (ie: using 'main' branch, no tag available...)
        ext_uri = cls.get_schema_uri()
        return obj.stac_extensions is not None and any(uri == ext_uri for uri in obj.stac_extensions)

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> "RDPSExtension[T]":
        """Extend the given STAC Object with properties from the :stac-ext:`RDPS Extension <rdps>`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises
        ------
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Collection):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(RDPSExtension[T], CollectionRDPSExtension(obj))
        elif isinstance(obj, pystac.Item):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(RDPSExtension[T], ItemRDPSExtension(obj))
        elif isinstance(obj, pystac.Asset):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(RDPSExtension[T], AssetRDPSExtension(obj))
        elif isinstance(obj, item_assets.AssetDefinition):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(RDPSExtension[T], ItemAssetsRDPSExtension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))

    @classmethod
    def summaries(cls, obj: pystac.Collection, add_if_missing: bool = False) -> "SummariesRDPSExtension":
        """Return the extended summaries object for the given collection."""
        cls.ensure_has_extension(obj, add_if_missing)
        return SummariesRDPSExtension(obj)


class ItemRDPSExtension(RDPSExtension[pystac.Item]):
    """
    A concrete implementation of :class:`RDPSExtension` on an :class:`~pystac.Item`.

    Extends the properties of the Item to include properties defined in the
    :stac-ext:`RDPS Extension <rdps>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`RDPSExtension.ext` on an :class:`~pystac.Item` to extend it.
    """

    def __init__(self, item: pystac.Item) -> None:
        self.item = item
        self.properties = item.properties

    def get_assets(
        self,
        service_type: Optional[ServiceType] = None,
    ) -> dict[str, pystac.Asset]:
        """Get the item's assets where eo:bands are defined.

        Args:
            service_type: If set, filter the assets such that only those with a
                matching :class:`~STACpopulator.stac_utils.ServiceType` are returned.

        Returns
        -------
            Dict[str, Asset]: A dictionary of assets that match ``service_type``
                if set or else all of this item's assets were service types are defined.
        """
        return {
            key: asset
            for key, asset in self.item.get_assets().items()
            if (service_type is ServiceType and service_type.value in asset.extra_fields)
            or any(ServiceType.from_value(field, default=None) is ServiceType for field in asset.extra_fields)
        }

    def __repr__(self) -> str:
        """Return repr."""
        return f"<ItemRDPSExtension Item id={self.item.id}>"


class ItemAssetsRDPSExtension(RDPSExtension[item_assets.AssetDefinition]):
    """Extention for RDPS item assets."""

    properties: dict[str, Any]
    asset_defn: item_assets.AssetDefinition

    def __init__(self, item_asset: item_assets.AssetDefinition) -> None:
        self.asset_defn = item_asset
        self.properties = item_asset.properties


class AssetRDPSExtension(RDPSExtension[pystac.Asset]):
    """
    A concrete implementation of :class:`RDPSExtension` on an :class:`~pystac.Asset`.

    Extends the Asset fields to include properties defined in the
    :stac-ext:`RDPS Extension <rdps>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`RDPSExtension.ext` on an :class:`~pystac.Asset` to extend it.
    """

    asset_href: str
    """The ``href`` value of the :class:`~pystac.Asset` being extended."""

    properties: dict[str, Any]
    """The :class:`~pystac.Asset` fields, including extension properties."""

    additional_read_properties: Optional[Iterable[dict[str, Any]]] = None
    """If present, this will be a list containing 1 dictionary representing the
    properties of the owning :class:`~pystac.Item`."""

    def __init__(self, asset: pystac.Asset) -> None:
        self.asset_href = asset.href
        self.properties = asset.extra_fields
        if asset.owner and isinstance(asset.owner, pystac.Item):
            self.additional_read_properties = [asset.owner.properties]

    def __repr__(self) -> str:
        """Return repr."""
        return f"<AssetRDPSExtension Asset href={self.asset_href}>"


class SummariesRDPSExtension(SummariesExtension):
    """
    A concrete implementation of :class:`~SummariesExtension`.

    Extends the ``summaries`` field of a :class:`~pystac.Collection` to include properties
    defined in the :stac-ext:`RDPS <rdps>`.
    """

    def _check_rdps_property(self, prop: str) -> FieldInfo:
        try:
            return RDPSProperties.model_fields[prop]
        except KeyError:
            raise AttributeError(f"Name '{prop}' is not a valid RDPS property.")

    def _validate_rdps_property(self, prop: str, summaries: list[Any]) -> None:
        model = RDPSProperties.model_construct()
        validator = RDPSProperties.__pydantic_validator__
        for value in summaries:
            validator.validate_assignment(model, prop, value)

    def get_rdps_property(self, prop: str) -> list[Any]:
        """Set RDPS property."""
        self._check_rdps_property(prop)
        return self.summaries.get_list(prop)

    def set_rdps_property(self, prop: str, summaries: list[Any]) -> None:
        """Set RDPS property."""
        self._check_rdps_property(prop)
        self._validate_rdps_property(prop, summaries)
        self._set_summary(prop, summaries)

    def __getattr__(self, prop: str) -> list[Any]:
        """Get RDPS property."""
        return self.get_rdps_property(prop)

    def __setattr__(self, prop: str, value: Any) -> None:
        """Set RDPS property."""
        self.set_rdps_property(prop, value)


class CollectionRDPSExtension(RDPSExtension[pystac.Collection]):
    """Extension for RDPS data."""

    def __init__(self, collection: pystac.Collection) -> None:
        self.collection = collection
