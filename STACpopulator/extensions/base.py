from datetime import datetime
import json
import jsonschema
from typing import Any, Dict, Generic,    TypeVar, Union, cast, Optional
from pydantic import (BaseModel, create_model, Field, FilePath, field_validator, model_validator, HttpUrl, ConfigDict,
                      PrivateAttr)
import pystac
from pystac.extensions import item_assets
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
    SummariesExtension,
)
from pystac import STACValidationError
from pystac.extensions.base import S  # generic pystac.STACObject
from STACpopulator.models import AnyGeometry, GeoJSONPolygon
from STACpopulator.stac_utils import (
    ServiceType,
    ncattrs_to_bbox,
    ncattrs_to_geometry,
)
import types
from pystac.extensions.datacube import DatacubeExtension
from STACpopulator.extensions.datacube import DataCubeHelper
from STACpopulator.extensions.thredds import THREDDSExtension, THREDDSHelper



T = TypeVar("T", pystac.Collection, pystac.Item, pystac.Asset, item_assets.AssetDefinition)


"""
# Context

What we have:
  - `Loader`, which returns attributes.
  - An external json schema describing a subset of the attributes returned by the Loader. This schema might preclude
  additional properties, so it cannot be applied wholesale to the Loader's output.
  - `data model` describing the content we want included in the catalog. It includes a subset of the schema properties,
  as well as additional attributes desired by the catalog admins.

Desiderata:
  - Not having to replicate existing validation logic in the schema
  - Not having to create a modified schema
  - Being able to supplement the schema validation by pydantic validation logic
  - Streamline the creation of new data models (reduce boilerplate, allow subclassing)
  - Developer-friendly validation error messages


How-to:
  - Instructions to create basic datamodel from schema (codegen)
  
  
  
"""
class DataModel(BaseModel):
    """Base class for dataset properties going into the catalog.

    Subclass this with attributes.
    """
    # Ideally, the catalog properties would be described by a jsonschema.
    _prefix: str = PrivateAttr()

    # URI of the json schema to validate against.
    _schema_uri: FilePath = PrivateAttr(None)

    # List of properties not meant to be validated by json schema.
    _schema_exclude: list[str] = PrivateAttr([])

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def validate_jsonschema(cls, data):
        """Validate the data model against the json schema, if given."""
        # Load schema
        uri =  cls._schema_uri.default
        if uri is not None:
            schema = json.load(open(uri))
            validator_cls = jsonschema.validators.validator_for(schema)
            validator_cls.check_schema(schema)
            validator = validator_cls(schema)

            attrs = {f"{cls._prefix.default}:{k}": v for (k,v) in data.items() if k not in cls._schema_exclude.default}
            errors = list(validator.iter_errors(attrs))
            if errors:
                raise ValueError(errors)

        return data


class THREDDSCatalogDataModel(BaseModel):
    """Base class ingesting attributes loaded by `THREDDSLoader` and creating a STAC item.

    This is meant to be subclassed for each extension.

    It includes two validation mechanisms:
     - pydantic validation using type hints, and
     - json schema validation.
    """

    # Fields required by STAC item creation
    geometry: GeoJSONPolygon
    bbox: list[float]
    start_datetime: datetime
    end_datetime: datetime

    # Extensions helper classes
    properties: DataModel
    datacube: DataCubeHelper
    thredds: THREDDSHelper

    # Private attributes used to validate schema properties
    model_config = ConfigDict(populate_by_name=True, extra="ignore", arbitrary_types_allowed=True)

    @classmethod
    def from_data(cls, data):
        """Instantiate class from data provided by THREDDS Loader."""
        return cls(start_datetime=data["groups"]["CFMetadata"]["attributes"]["time_coverage_start"],
                   end_datetime=data["groups"]["CFMetadata"]["attributes"]["time_coverage_end"],
                   geometry=ncattrs_to_geometry(data),
                   bbox=ncattrs_to_bbox(data),
                   properties=data["attributes"],
                   datacube=DataCubeHelper(data),  # A bit clunky to avoid breaking CMIP6
                   thredds=THREDDSHelper(data["access_urls"])
                   )

    @property
    def uid(self) -> str:
        """Return a unique ID. When subclassing, use a combination of properties uniquely identifying a dataset."""
        import uuid
        return str(uuid.uuid4())

    # @field_validator("access_urls")
    # @classmethod
    # def validate_access_urls(cls, value):
    #     assert len(set(["HTTPServer", "OPENDAP"]).intersection(value.keys())) >= 1, (
    #         "Access URLs must include HTTPServer or OPENDAP keys.")
    #     return value

    def stac_item(self) -> "pystac.Item":
        item = pystac.Item(
            id=self.uid,
            geometry=self.geometry.model_dump(),
            bbox=self.bbox,
            properties={
                "start_datetime": str(self.start_datetime),
                "end_datetime": str(self.end_datetime),
            },
            datetime=None,
        )

        # self.metadata_extension(item)
        self.datacube_extension(item)
        self.thredds_extension(item)

        try:
            item.validate()
        except STACValidationError as e:
            raise Exception("Failed to validate STAC item") from e

        # print(json.dumps(item.to_dict()))
        return json.loads(json.dumps(item.to_dict()))


    def metadata_extension(self, item):
        ExtSubCls = metacls_extension(self.properties._prefix, schema_uri=str(self.properties._schema_uri))
        item_ext = ExtSubCls.ext(item, add_if_missing=False)
        item_ext.apply(self.properties.model_dump(mode="json", by_alias=True))
        return item

    def datacube_extension(self, item):
        dc_ext = DatacubeExtension.ext(item, add_if_missing=True)
        dc_ext.apply(dimensions=self.datacube.dimensions, variables=self.datacube.variables)

    def thredds_extension(self, item):
        thredds_ext = THREDDSExtension.ext(item, add_if_missing=False)
        thredds_ext.apply(self.thredds.services, self.thredds.links)


def metacls_extension(name, schema_uri):
        cls_name = f"{name.upper()}Extension"

        bases = (MetaExtension,
                 Generic[T],
                 PropertiesExtension,
                 ExtensionManagementMixin[Union[pystac.Asset, pystac.Item, pystac.Collection]]
                 )

        attrs = {"schema_name": name, "schema_uri": schema_uri}
        return types.new_class(name=cls_name, bases=bases, kwds=None, exec_body=lambda ns: ns.update(attrs))


def extend_type(stac, cls, ext):
    cls_name = f"{stac.__name__ }{ext.__name__}"
    return types.new_class(cls_name, (cls, ext), {}, lambda ns: ns)


class MetaExtension:
    schema_name: str
    schema_uri: str

    @property
    def name(self) -> str:
        return self.schema_name

    def apply(self, properties: dict[str, Any]) -> None:
        """Applies CMIP6 Extension properties to the extended
        :class:`~pystac.Item` or :class:`~pystac.Asset`.
        """
        for prop, val in properties.items():
            self._set_property(prop, val)

    @classmethod
    def get_schema_uri(cls) -> str:
        """We have already validated the JSON schema."""
        return cls.schema_uri

    @classmethod
    def has_extension(cls, obj: S):
        # FIXME: this override should be removed once an official and versioned schema is released
        # ignore the original implementation logic for a version regex
        # since in our case, the VERSION_REGEX is not fulfilled (ie: using 'main' branch, no tag available...)
        ext_uri = cls.get_schema_uri()
        return obj.stac_extensions is not None and any(uri == ext_uri for uri in obj.stac_extensions)

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> "Extension[T]":
        """Extends the given STAC Object with properties from the
        :stac-ext:`Extension`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises:

            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        cls_map = {pystac.Item: MetaItemExtension}

        for key, meta in cls_map.items():
            if isinstance(obj, key):
                cls.ensure_has_extension(obj, add_if_missing)
                kls = extend_type(key, meta, cls[key])
                return cast(cls[T], kls(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))


class MetaItemExtension:
    """A concrete implementation of :class:`CMIP6Extension` on an :class:`~pystac.Item`
    that extends the properties of the Item to include properties defined in the
    :stac-ext:`Extension`.

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

        Returns:
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
        return f"<{self.__class__.__name__} Item id={self.item.id}>"


def schema_properties(schema: dict) -> list[str]:
    """Return the list of properties described by schema."""
    out = []
    for key, val in schema["properties"].items():
        prefix, name = key.split(":") if ":" in key else (None, key)
        out.append(name)
    return out


def model_from_schema(model_name, schema: dict):
    """Create pydantic BaseModel from JSON schema."""
    type_map = {"string": str, "number": float, "integer": int, "boolean": bool, "array": list, "object": dict,
                None: Any}

    fields = {}
    for key, val in schema["properties"].items():
        prefix, name = key.split(":") if ":" in key else (None, key)
        typ = type_map[val.get("type")]
        default = ... if key in schema["required"] else None
        fields[name] = (typ, Field(default, alias=key))
    return create_model(model_name, **fields)

