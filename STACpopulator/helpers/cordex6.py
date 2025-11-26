from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import FilePath

from STACpopulator.helpers.base import ExtensionHelper


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
