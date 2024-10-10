from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field, FilePath
from datetime import datetime

from importlib import reload
import STACpopulator.extensions.base
reload(STACpopulator.extensions.base)
from STACpopulator.extensions.base import THREDDSCatalogDataModel, DataModel


# This is generated using datamodel-codegen + manual edits
class CordexCmip6(DataModel):
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
        name = "_".join(getattr(self.properties, k) for k in keys)
        return name




def get_test_data():
    import requests
    from siphon.catalog import TDSCatalog
    import xncml
    from STACpopulator.stac_utils import numpy_to_python_datatypes

    cat = TDSCatalog("https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/disk2/ouranos/CORDEX/CMIP6/DD/NAM-12/OURANOS/MPI-ESM1-2-LR/ssp370/r1i1p1f1/CRCM5/v1-r1/day/tas/v20231208/catalog.html")

    if cat.datasets.items():
        for item_name, ds in cat.datasets.items():
            url = ds.access_urls["NCML"]
            r = requests.get(url)
            attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
            attrs["attributes"] = numpy_to_python_datatypes(attrs["attributes"])
            attrs["access_urls"] = ds.access_urls
            return attrs

def test_item():
    attrs = get_test_data()
    model = Cordex6DataModel.from_data(attrs)
    model.stac_item()

