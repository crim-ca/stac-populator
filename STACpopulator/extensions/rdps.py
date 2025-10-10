from __future__ import annotations

from pydantic import model_validator

from STACpopulator.extensions.cf import CFHelper
from STACpopulator.extensions.file import FileHelper
from STACpopulator.extensions.thredds import THREDDSCatalogDataModel


# Customize the THREDDSCatalogDataModel
class RDPSDataModel(THREDDSCatalogDataModel):
    """Data model for RDPS NetCDF datasets."""

    # Extension classes
    cf: CFHelper
    file: FileHelper

    @model_validator(mode="before")
    @classmethod
    def cf_helper(cls, data: dict) -> dict:
        """Instantiate the cf helper."""
        data["cf"] = CFHelper(data["data"]["variables"])
        return data

    @model_validator(mode="before")
    @classmethod
    def file_helper(cls, data: dict) -> dict:
        """Instantiate the file helper."""
        data["file"] = FileHelper(data["data"]["variables"])
        return data
