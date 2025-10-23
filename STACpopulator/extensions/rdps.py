from __future__ import annotations

from pydantic import model_validator
from requests import Session

from STACpopulator.extensions.cf import CFHelper
from STACpopulator.extensions.file import FileHelper
from STACpopulator.extensions.thredds import THREDDSCatalogDataModel


class RDPSDataModel(THREDDSCatalogDataModel):
    """Data model for RDPS NetCDF datasets."""

    # Extension classes
    cf: CFHelper
    file: FileHelper

    @model_validator(mode="before")
    @classmethod
    def cf_helper(cls, data: dict) -> dict:
        """Instantiate the cf helper."""
        field = "cf"
        data[field] = cls.helper_class(field)(variables=data["data"]["variables"])
        return data

    @model_validator(mode="before")
    @classmethod
    def file_helper(cls, data: dict) -> dict:
        """Instantiate the file helper."""
        field = "file"
        data[field] = cls.helper_class(field)(access_urls=data["data"]["access_urls"])
        return data

    @classmethod
    def helper_class(cls, field_name: str) -> type[any]:
        """Return type annotation of a model field."""
        # TODO: Should maybe be moved to parent for reuse?
        return cls.model_fields[field_name].annotation

    def set_session(self, session: Session) -> None:
        """Set session parameter to helper(s)."""
        self.file.session = session
