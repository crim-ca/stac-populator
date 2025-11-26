# Customize the THREDDSCatalogDataModel
from pydantic import model_validator

from STACpopulator.datamodels.thredds import THREDDSCatalogDataModel
from STACpopulator.helpers.cordex6 import CordexCmip6
from STACpopulator.helpers.xscen import Xscen


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
