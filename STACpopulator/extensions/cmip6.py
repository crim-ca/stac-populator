"""CMIP6 extension based on https://stac-extensions.github.io/cmip6/v1.0.0/schema.json"""

import json
from typing import Generic, TypeVar, Union, cast

import pystac
from pystac.extensions.base import ExtensionManagementMixin, PropertiesExtension
from pystac.extensions.hooks import ExtensionHooks

from datetime import date, datetime
from typing import Any, Dict, List, Literal
import pyessv
from pydantic import (
    AnyHttpUrl,
    FieldValidationInfo,
    field_validator,
    model_serializer,
)
from pydantic.networks import Url


from STACpopulator.stac_utils import ItemProperties
from STACpopulator.stac_utils import collection2literal

T = TypeVar("T", pystac.Collection, pystac.Item, pystac.Asset)

SCHEMA_URI = "https://stac-extensions.github.io/cmip6/v1.0.0/schema.json"

prefix: str = "cmip6:"


# CMIP6 controlled vocabulary (CV)
CV = pyessv.WCRP.CMIP6

# Enum classes built from the pyessv' CV
ActivityID = collection2literal(CV.activity_id)
ExperimentID = collection2literal(CV.experiment_id)
Frequency = collection2literal(CV.frequency)
GridLabel = collection2literal(CV.grid_label)
InstitutionID = collection2literal(CV.institution_id)
NominalResolution = collection2literal(CV.nominal_resolution)
Realm = collection2literal(CV.realm)
SourceID = collection2literal(CV.source_id)
SourceType = collection2literal(CV.source_type)
SubExperimentID = collection2literal(CV.sub_experiment_id)
TableID = collection2literal(CV.table_id)


class Properties(ItemProperties, validate_assignment=True):
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
    sub_experiment_id: Union[SubExperimentID, Literal["none"]]
    table_id: TableID
    variable_id: str
    variant_label: str
    initialization_index: int
    physics_index: int
    realization_index: int
    forcing_index: int
    tracking_id: str
    version: str
    product: str
    license: str
    grid: str
    mip_era: str

    #@model_serializer
    def serialize_extension(self) -> str:
        """Add prefix to all fields."""

        def json_encode(obj):
            if isinstance(obj, Url):
                return str(obj)
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        data = {prefix + k: v for k, v in self.model_dump().items()}
        return json.dumps(data, default=json_encode)

    @field_validator("initialization_index", "physics_index", "realization_index", "forcing_index", mode="before")
    @classmethod
    def first_item(cls, v: list, info: FieldValidationInfo):
        """Pick single item from list."""
        assert len(v) == 1, f"{info.field_name} must have one item only."
        return v[0]

    @field_validator("realm", "source_type", mode="before")
    @classmethod
    def split(cls, v: str, info: FieldValidationInfo):
        """Split string into list."""
        return v.split(" ")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str, info: FieldValidationInfo):
        assert v[0] == "v", "Version string should begin with a lower case 'v'"
        assert v[1:].isdigit(), "All characters in version string, except first, should be digits"
        return v


class CMIP6Extension(Generic[T], ExtensionManagementMixin[pystac.Item], PropertiesExtension):
    """An abstract class that can be used to extend the properties of a
    :class:`~pystac.Item` with properties from the :stac-ext:`CMIP6 Extension <cmip6>`.

    To create an instance of :class:`CMIP6Extension`, use the :meth:`CMIP6Extension.ext` method.
    """
    def apply(self, attrs: Dict[str, Any]) -> None:
        """Applies Datacube Extension properties to the extended
        :class:`~pystac.Collection`, :class:`~pystac.Item` or :class:`~pystac.Asset`.

        Args:
            dimensions : Dictionary mapping dimension name to :class:`Dimension`
                objects.
            variables : Dictionary mapping variable name to a :class:`Variable`
                object.
        """
        self.properties.update(**Properties(**attrs).model_dump())

    @classmethod
    def get_schema_uri(cls) -> str:
        return SCHEMA_URI
    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False):
        """Extends the given STAC Object with properties from the :stac-ext:`CMIP6
        Extension <cmip6>`.

        This extension can be applied to instances of :class:`~pystac.Item`.

        Raises:
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Item):
            cls.validate_has_extension(obj, add_if_missing)
            return cast(CMIP6Extension[T], ItemCMIP6Extension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))


class ItemCMIP6Extension(CMIP6Extension[pystac.Item]):
    """A concrete implementation of :class:`DatacubeExtension` on an
    :class:`~pystac.Item` that extends the properties of the Item to include properties
    defined in the :stac-ext:`Datacube Extension <datacube>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`DatacubeExtension.ext` on an :class:`~pystac.Item` to extend it.
    """

    item: pystac.Item
    properties: Dict[str, Any]

    def __init__(self, item: pystac.Item):
        self.item = item
        self.properties = item.properties

    def __repr__(self) -> str:
        return "<ItemCMIP6Extension Item id={}>".format(self.item.id)


class CMIP6ExtensionHooks(ExtensionHooks):
    schema_uri: str = SCHEMA_URI
    prev_extension_ids = {"cmip6"}
    stac_object_types = {pystac.STACObjectType.ITEM}


CMIP6_EXTENSION_HOOKS: ExtensionHooks = CMIP6ExtensionHooks()
