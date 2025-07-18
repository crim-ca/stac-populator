from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import FilePath, model_validator

from STACpopulator.extensions.base import ExtensionHelper
from STACpopulator.extensions.thredds import THREDDSCatalogDataModel
from STACpopulator.extensions.xscen import Xscen


# This is generated using datamodel-codegen + manual edits
class CordexCmip6(ExtensionHelper):
    """Helper for CORDEX CMIP6 data."""

    # Fields from schema
    activity_id: str
    contact: str
    # Conventions: str = Field(..., alias='cordex6:Conventions')
    creation_date: datetime
    domain_id: str
    domain: str
    driving_experiment_id: str
    driving_experiment: str
    driving_institution_id: str
    driving_source_id: str
    driving_variant_label: str
    frequency: str
    grid: str
    institution: str
    institution_id: str
    license: str
    mip_era: str
    product: str
    project_id: str
    source: str
    source_id: str
    source_type: str
    tracking_id: str
    variable_id: str
    version_realization: str

    # Extra fields
    external_variables: str | list[str]

    _prefix = "cordex6"
    # Note that this is not a STAC item schema, but a schema for the global attributes of the CMIP6 data.
    _schema_uri: FilePath = Path(__file__).parent / "schemas" / "cordex6" / "cmip6-cordex-global-attrs-schema.json"


# Customize the THREDDSCatalogDataModel
class Cordex6DataModel(THREDDSCatalogDataModel):
    """Data model for CORDEX-CMIP6 NetCDF datasets."""

    cordex6: CordexCmip6

    def create_uid(self) -> str:
        """Return a unique ID for CMIP6 data item."""
        keys = [
            "activity_id",
            "driving_institution_id",
            "driving_source_id",
            "institution_id",
            "source_id",
            "driving_experiment_id",
            "driving_variant_label",
            "version_realization",
            "variable_id",
            "domain_id",
            "frequency",
        ]
        values = [getattr(self.cordex6, k) for k in keys]
        values.append(self.start_datetime.strftime("%Y%m%d"))
        values.append(self.end_datetime.strftime("%Y%m%d"))
        return "_".join(values)

    @model_validator(mode="before")
    @classmethod
    def properties_helper(cls, data: dict) -> dict:
        """Instantiate the properties helper."""
        data["cordex6"] = data["data"]["attributes"]
        return data


# Customize the THREDDSCatalogDataModel
class Cordex6DataModelNcML(Cordex6DataModel):
    """Data model for CORDEX-CMIP6 NcML aggregations."""

    xscen: Xscen

    @model_validator(mode="before")
    @classmethod
    def xscen_helper(cls, data: dict) -> dict:
        """Instantiate the XSCEN helper."""
        data["xscen"] = data["data"]["attributes"]
        return data
