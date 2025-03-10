import json
from datetime import datetime
from typing import (
    Any,
    Generic,
    Iterable,
    List,
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
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    FieldValidationInfo,
    field_validator,
)
from pydantic.fields import FieldInfo
from pystac.extensions import item_assets
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
    S,  # generic pystac.STACObject
    SummariesExtension,
)

from STACpopulator.exceptions import ExtensionLoadError
from STACpopulator.models import AnyGeometry
from STACpopulator.stac_utils import (
    ServiceType,
    collection2literal,
    ncattrs_to_bbox,
    ncattrs_to_geometry,
)

try:
    import pyessv
except OSError as e:
    raise ExtensionLoadError(str(e)) from e

T = TypeVar("T", pystac.Collection, pystac.Item, pystac.Asset, item_assets.AssetDefinition)

SchemaName = Literal["cmip6"]
# FIXME: below reference (used as ID in the schema itself) should be updated once the extension is officially released
# SCHEMA_URI: str = "https://raw.githubusercontent.com/stac-extensions/cmip6/refs/heads/main/json-schema/schema.json"
# below is the temporary resolvable URI
SCHEMA_URI: str = "https://raw.githubusercontent.com/dchandan/stac-extension-cmip6/main/json-schema/schema.json"
PREFIX = f"{get_args(SchemaName)[0]}:"

# CMIP6 controlled vocabulary (CV)
CV = pyessv.WCRP.CMIP6  # noqa

# Enum classes built from the pyessv' CV
ActivityID = collection2literal(CV.activity_id)
ExperimentID = collection2literal(CV.experiment_id)
Frequency = collection2literal(CV.frequency)
GridLabel = collection2literal(CV.grid_label)
InstitutionID = collection2literal(CV.institution_id)
NominalResolution = collection2literal(CV.nominal_resolution)
Realm = collection2literal(CV.realm)
SourceID = collection2literal(CV.source_id, "source_id")
SourceType = collection2literal(CV.source_type)
SubExperimentID = collection2literal(CV.sub_experiment_id)
TableID = collection2literal(CV.table_id)


def add_cmip6_prefix(name: str) -> str:
    return PREFIX + name if "datetime" not in name else name


class CMIP6Properties(BaseModel, validate_assignment=True):
    """Data model for CMIP6 Controlled Vocabulary."""

    Conventions: str
    activity_id: ActivityID
    creation_date: datetime
    data_specs_version: str
    experiment: str
    experiment_id: ExperimentID
    frequency: Frequency
    further_info_url: AnyHttpUrl
    grid_label: GridLabel
    institution: str
    institution_id: InstitutionID
    nominal_resolution: NominalResolution
    realm: List[Realm]
    source: str
    source_id: SourceID
    source_type: List[SourceType]
    sub_experiment: Union[str, Literal["none"]]
    sub_experiment_id: SubExperimentID | Literal["none"]
    table_id: TableID
    variable_id: str
    variant_label: str
    initialization_index: int
    physics_index: int
    realization_index: int
    forcing_index: int
    tracking_id: str = Field("")
    version: str = Field("")
    product: str
    license: str
    grid: str
    mip_era: str

    model_config = ConfigDict(alias_generator=add_cmip6_prefix, populate_by_name=True, extra="ignore")

    @field_validator("initialization_index", "physics_index", "realization_index", "forcing_index", mode="before")
    @classmethod
    def only_item(cls, v: list[int], info: FieldValidationInfo):
        """Pick single item from list."""
        assert len(v) == 1, f"{info.field_name} must have one item only."
        return v[0]

    @field_validator("realm", "source_type", mode="before")
    @classmethod
    def split(cls, v: str, __info: FieldValidationInfo):
        """Split string into list."""
        return v.split(" ")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str, __info: FieldValidationInfo):
        assert v[0] == "v", "Version string should begin with a lower case 'v'"
        assert v[1:].isdigit(), "All characters in version string, except first, should be digits"
        return v


class CMIP6Helper:
    def __init__(self, attrs: MutableMapping[str, Any], geometry_model: Type[AnyGeometry]):
        self.attrs = attrs
        self.cmip6_attrs = attrs["attributes"]
        self.cfmeta = attrs["groups"]["CFMetadata"]["attributes"]
        self.geometry_model = geometry_model

    @property
    def uid(self) -> str:
        """Return a unique ID for CMIP6 data item."""
        keys = [
            "activity_id",
            "institution_id",
            "source_id",
            "experiment_id",
            "variant_label",
            "table_id",
            "variable_id",
            "grid_label",
        ]
        name = "_".join(self.cmip6_attrs[k] for k in keys)
        return name

    @property
    def geometry(self) -> AnyGeometry:
        return self.geometry_model(**ncattrs_to_geometry(self.attrs))

    @property
    def bbox(self) -> list[float]:
        return ncattrs_to_bbox(self.attrs)

    @property
    def start_datetime(self) -> datetime:
        return self.cfmeta["time_coverage_start"]

    @property
    def end_datetime(self) -> datetime:
        return self.cfmeta["time_coverage_end"]

    @property
    def properties(self) -> CMIP6Properties:
        props = CMIP6Properties(**self.cmip6_attrs)
        return props

    def stac_item(self) -> "pystac.Item":
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
        item_cmip6 = CMIP6Extension.ext(item, add_if_missing=True)
        item_cmip6.apply(self.properties)
        return item


class CMIP6Extension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[Union[pystac.Asset, pystac.Item, pystac.Collection]],
):
    @property
    def name(self) -> SchemaName:
        return get_args(SchemaName)[0]

    def apply(
        self,
        properties: Union[CMIP6Properties, dict[str, Any]],
    ) -> None:
        """Applies CMIP6 Extension properties to the extended
        :class:`~pystac.Item` or :class:`~pystac.Asset`.
        """
        if isinstance(properties, dict):
            properties = CMIP6Properties(**properties)
        data_json = json.loads(properties.model_dump_json(by_alias=True))
        for prop, val in data_json.items():
            self._set_property(prop, val)

    @classmethod
    def get_schema_uri(cls) -> str:
        return SCHEMA_URI

    @classmethod
    def has_extension(cls, obj: S):
        # FIXME: this override should be removed once an official and versioned schema is released
        # ignore the original implementation logic for a version regex
        # since in our case, the VERSION_REGEX is not fulfilled (ie: using 'main' branch, no tag available...)
        ext_uri = cls.get_schema_uri()
        return obj.stac_extensions is not None and any(uri == ext_uri for uri in obj.stac_extensions)

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> "CMIP6Extension[T]":
        """Extends the given STAC Object with properties from the
        :stac-ext:`CMIP6 Extension <cmip6>`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises
        ------
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Collection):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(CMIP6Extension[T], CollectionCMIP6Extension(obj))
        elif isinstance(obj, pystac.Item):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(CMIP6Extension[T], ItemCMIP6Extension(obj))
        elif isinstance(obj, pystac.Asset):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(CMIP6Extension[T], AssetCMIP6Extension(obj))
        elif isinstance(obj, item_assets.AssetDefinition):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(CMIP6Extension[T], ItemAssetsCMIP6Extension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))

    @classmethod
    def summaries(cls, obj: pystac.Collection, add_if_missing: bool = False) -> "SummariesCMIP6Extension":
        """Returns the extended summaries object for the given collection."""
        cls.ensure_has_extension(obj, add_if_missing)
        return SummariesCMIP6Extension(obj)


class ItemCMIP6Extension(CMIP6Extension[pystac.Item]):
    """A concrete implementation of :class:`CMIP6Extension` on an :class:`~pystac.Item`
    that extends the properties of the Item to include properties defined in the
    :stac-ext:`CMIP6 Extension <cmip6>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`CMIP6Extension.ext` on an :class:`~pystac.Item` to extend it.
    """

    def __init__(self, item: pystac.Item):
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
        return f"<ItemCMIP6Extension Item id={self.item.id}>"


class ItemAssetsCMIP6Extension(CMIP6Extension[item_assets.AssetDefinition]):
    properties: dict[str, Any]
    asset_defn: item_assets.AssetDefinition

    def __init__(self, item_asset: item_assets.AssetDefinition):
        self.asset_defn = item_asset
        self.properties = item_asset.properties


class AssetCMIP6Extension(CMIP6Extension[pystac.Asset]):
    """A concrete implementation of :class:`CMIP6Extension` on an :class:`~pystac.Asset`
    that extends the Asset fields to include properties defined in the
    :stac-ext:`CMIP6 Extension <cmip6>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`CMIP6Extension.ext` on an :class:`~pystac.Asset` to extend it.
    """

    asset_href: str
    """The ``href`` value of the :class:`~pystac.Asset` being extended."""

    properties: dict[str, Any]
    """The :class:`~pystac.Asset` fields, including extension properties."""

    additional_read_properties: Optional[Iterable[dict[str, Any]]] = None
    """If present, this will be a list containing 1 dictionary representing the
    properties of the owning :class:`~pystac.Item`."""

    def __init__(self, asset: pystac.Asset):
        self.asset_href = asset.href
        self.properties = asset.extra_fields
        if asset.owner and isinstance(asset.owner, pystac.Item):
            self.additional_read_properties = [asset.owner.properties]

    def __repr__(self) -> str:
        return f"<AssetCMIP6Extension Asset href={self.asset_href}>"


class SummariesCMIP6Extension(SummariesExtension):
    """A concrete implementation of :class:`~SummariesExtension` that extends
    the ``summaries`` field of a :class:`~pystac.Collection` to include properties
    defined in the :stac-ext:`CMIP6 <cmip6>`.
    """

    def _check_cmip6_property(self, prop: str) -> FieldInfo:
        try:
            return CMIP6Properties.model_fields[prop]
        except KeyError:
            raise AttributeError(f"Name '{prop}' is not a valid CMIP6 property.")

    def _validate_cmip6_property(self, prop: str, summaries: list[Any]) -> None:
        model = CMIP6Properties.model_construct()
        validator = CMIP6Properties.__pydantic_validator__
        for value in summaries:
            validator.validate_assignment(model, prop, value)

    def get_cmip6_property(self, prop: str) -> list[Any]:
        self._check_cmip6_property(prop)
        return self.summaries.get_list(prop)

    def set_cmip6_property(self, prop: str, summaries: list[Any]) -> None:
        self._check_cmip6_property(prop)
        self._validate_cmip6_property(prop, summaries)
        self._set_summary(prop, summaries)

    def __getattr__(self, prop):
        return self.get_cmip6_property(prop)

    def __setattr__(self, prop, value):
        self.set_cmip6_property(prop, value)


class CollectionCMIP6Extension(CMIP6Extension[pystac.Collection]):
    def __init__(self, collection: pystac.Collection):
        self.collection = collection
