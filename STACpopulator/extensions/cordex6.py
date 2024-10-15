from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field, FilePath
from datetime import datetime

from importlib import reload
import STACpopulator.extensions.base
reload(STACpopulator.extensions.base)
from STACpopulator.extensions.base import THREDDSCatalogDataModel, DataModelHelper


# This is generated using datamodel-codegen + manual edits
class CordexCmip6(DataModelHelper):
    # Fields from schema
    activity_id: str = Field(..., alias='cordex6:activity_id')
    contact: str = Field(..., alias='cordex6:contact')
    # Conventions: str = Field(..., alias='cordex6:Conventions')
    creation_date: datetime = Field(..., alias='cordex6:creation_date')
    domain_id: str = Field(..., alias='cordex6:domain_id')
    domain: str = Field(..., alias='cordex6:domain')
    driving_experiment_id: str = Field(..., alias='cordex6:driving_experiment_id')
    driving_experiment: str = Field(..., alias='cordex6:driving_experiment')
    driving_institution_id: str = Field(..., alias='cordex6:driving_institution_id')
    driving_source_id: str = Field(..., alias='cordex6:driving_source_id')
    driving_variant_label: str = Field(..., alias='cordex6:driving_variant_label')
    frequency: str = Field(..., alias='cordex6:frequency')
    grid: str = Field(..., alias='cordex6:grid')
    institution: str = Field(..., alias='cordex6:institution')
    institution_id: str = Field(..., alias='cordex6:institution_id'    )
    license: str = Field(..., alias='cordex6:license')
    mip_era: str = Field(..., alias='cordex6:mip_era')
    product: str = Field(..., alias='cordex6:product')
    project_id: str = Field(..., alias='cordex6:project_id')
    source: str = Field(..., alias='cordex6:source')
    source_id: str = Field(..., alias='cordex6:source_id')
    source_type: str = Field(..., alias='cordex6:source_type')
    tracking_id: str = Field(..., alias='cordex6:tracking_id')
    variable_id: str = Field(..., alias='cordex6:variable_id')
    version_realization: str = Field(..., alias='cordex6:version_realization')

    # Extra fields
    external_variables: str | list[str]

    _prefix: str = "cordex6"
    # Note that this is not a STAC item schema, but a schema for the global attributes of the CMIP6 data.
    _schema_uri: FilePath = Path(__file__).parent / "schemas" / "cordex6" / "cmip6-cordex-global-attrs-schema.json"


# Customize the THREDDSCatalogDataModel
class Cordex6DataModel(THREDDSCatalogDataModel):
    properties: CordexCmip6

    @property
    def uid(self) -> str:
        """Return a unique ID for CMIP6 data item."""
        keys = [
            "activity_id",
            "driving_institution_id",
            "driving_source_id",
            "institution_id",
            "source_id",
            "driving_experiment_id",
            "driving_variant_label",
            "variable_id",
            "domain_id",
        ]
        values = [getattr(self.properties, k) for k in keys]
        values.append(self.start_datetime.strftime("%Y%m%d"))
        values.append(self.end_datetime.strftime("%Y%m%d"))
        return "_".join(values)



