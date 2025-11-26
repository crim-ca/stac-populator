import json
import tempfile
from abc import abstractmethod
from pathlib import Path
from typing import Any

import jsonschema
import pystac
from pydantic import BaseModel, ConfigDict, FilePath, PrivateAttr, model_validator

from STACpopulator.extensions.base import metacls_extension


class Helper:
    """Class to be subclassed by extension helpers."""

    @classmethod
    @abstractmethod
    def from_data(
        cls,
        data: dict[str, Any],
        **kwargs,
    ) -> "Helper":
        """Create a Helper instance from raw data."""
        pass


class ExtensionHelper(BaseModel, Helper):
    """Base class for dataset properties going into the catalog.

    Subclass this with attributes.

    Attributes
    ----------
    _prefix : str
        If not None, this prefix is added to ingested data before the jsonschema validation.
    _schema_uri : str
        URI of the json schema to validate against. Note this is not a STAC schema, but a schema for the dataset properties only.
    _schema_exclude : list[str]
        Properties not meant to be validated by json schema, but still included in the data model.
    """

    _prefix: str = PrivateAttr()
    _schema_uri: FilePath = PrivateAttr(None)
    _schema_exclude: list[str] = PrivateAttr([])

    model_config = ConfigDict(populate_by_name=True, extra="ignore", ser_json_inf_nan="strings")

    @classmethod
    def __init_subclass__(cls, **kwargs) -> None:
        """Automatically set an alias generator from the `_prefix`."""
        prefix = cls._prefix.default

        if prefix is not None:
            cls.model_config["alias_generator"] = lambda key: f"{prefix}:{key}"

    @model_validator(mode="before")
    @classmethod
    def validate_jsonschema(cls, data: dict) -> dict:
        """Validate the data model against the json schema, if given."""
        # Load schema
        uri = cls._schema_uri.default
        if uri is not None:
            with open(uri) as f:
                schema = json.load(f)
            validator_cls = jsonschema.validators.validator_for(schema)
            validator_cls.check_schema(schema)
            validator = validator_cls(schema)

            attrs = {f"{cls._prefix.default}:{k}": v for (k, v) in data.items() if k not in cls._schema_exclude.default}
            errors = list(validator.iter_errors(attrs))
            if errors:
                raise ValueError(errors)

        return data

    def apply(self, item: pystac.Item, add_if_missing: bool = True) -> pystac.Item:
        """
        Add extension for the properties of the dataset to the STAC item.

        The extension class is created dynamically from the properties.
        """
        schema_uri = self.write_stac_schema() if self._schema_uri else None
        ExtSubCls = metacls_extension(self._prefix, schema_uri=schema_uri)
        item_ext = ExtSubCls.ext(item, add_if_missing=add_if_missing)

        # Sanitize the output so it's json serializable.
        data = json.loads(self.model_dump_json(by_alias=True))

        item_ext.apply(data)
        return item

    def to_stac_schema(self) -> dict:
        """Return the STAC schema for the extension."""
        return {
            "type": "object",
            "required": ["type", "properties"],
            "properties": {"type": {"const": "Feature"}, "properties": {"$ref": str(self._schema_uri)}},
        }

    def write_stac_schema(self) -> str:
        """Write STAC schema to a temporary file and return that file path."""
        path = Path(tempfile.mkdtemp()) / f"{self._prefix}-schema.json"
        with open(path, "w") as fh:
            json.dump(self.to_stac_schema(), fh)
        return path
