import logging
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Literal, MutableMapping
from colorlog import ColoredFormatter
import argparse
import pyessv
from pydantic import AnyHttpUrl, BaseModel, Field, FieldValidationInfo, field_validator
from pystac.extensions.datacube import DatacubeExtension

from STACpopulator import STACpopulatorBase
from STACpopulator.extensions import cmip6
from STACpopulator.input import THREDDSLoader
from STACpopulator.stac_utils import ItemProperties
from STACpopulator.stac_utils import collection2literal, CFJsonItem


LOGGER = logging.getLogger(__name__)
LOGFORMAT = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s"
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setFormatter(formatter)
LOGGER.addHandler(stream)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

# CMIP6 controlled vocabulary (CV)
CV = pyessv.WCRP.CMIP6

# Enum classes built from the pyessv' CV
ActivityID = collection2literal(CV.activity_id)
ExperimentID = collection2literal(CV.experiment_id)
Frequency = collection2literal(CV.frequency)
GridLabel = collection2literal(CV.grid_label)
InstitutionID = collection2literal(CV.institution_id)
# Member = collection2literal(CV.member_id)  # This is empty
NominalResolution = collection2literal(CV.nominal_resolution)
Realm = collection2literal(CV.realm)
SourceID = collection2literal(CV.source_id)
SourceType = collection2literal(CV.source_type)
SubExperimentID = collection2literal(CV.sub_experiment_id)
TableID = collection2literal(CV.table_id)
# Variable = collection2literal(CV.variable_id)  # This is empty


class Properties(ItemProperties, validate_assignment=True):
    """Data model for CMIP6 Controlled Vocabulary."""

    Conventions: str = Field(..., serialization_alias="cmip6:Conventions")
    activity_id: ActivityID = Field(..., serialization_alias="cmip6:activity_id")
    creation_date: datetime = Field(..., serialization_alias="cmip6:creation_date")
    data_specs_version: str = Field(..., serialization_alias="cmip6:data_specs_version")
    experiment: str = Field(..., serialization_alias="cmip6:experiment")
    experiment_id: ExperimentID = Field(..., serialization_alias="cmip6:experiment_id")
    frequency: Frequency = Field(..., serialization_alias="cmip6:frequency")
    further_info_url: AnyHttpUrl = Field(..., serialization_alias="cmip6:further_info_url")
    grid_label: GridLabel = Field(..., serialization_alias="cmip6:grid_label")
    institution: str = Field(..., serialization_alias="cmip6:institution")
    institution_id: InstitutionID = Field(..., serialization_alias="cmip6:institution_id")
    nominal_resolution: NominalResolution = Field(..., serialization_alias="cmip6:nominal_resolution")
    realm: List[Realm] = Field(..., serialization_alias="cmip6:realm")
    source: str = Field(..., serialization_alias="cmip6:source")
    source_id: SourceID = Field(..., serialization_alias="cmip6:source_id")
    source_type: List[SourceType] = Field(..., serialization_alias="cmip6:source_type")
    sub_experiment: str | Literal["none"] = Field(..., serialization_alias="cmip6:sub_experiment")
    sub_experiment_id: SubExperimentID | Literal["none"] = Field(..., serialization_alias="cmip6:sub_experiment_id")
    table_id: TableID = Field(..., serialization_alias="cmip6:table_id")
    variable_id: str = Field(..., serialization_alias="cmip6:variable_id")
    variant_label: str = Field(..., serialization_alias="cmip6:variant_label")
    initialization_index: int = Field(..., serialization_alias="cmip6:initialization_index")
    physics_index: int = Field(..., serialization_alias="cmip6:physics_index")
    realization_index: int = Field(..., serialization_alias="cmip6:realization_index")
    forcing_index: int = Field(..., serialization_alias="cmip6:forcing_index")
    tracking_id: str = Field(..., serialization_alias="cmip6:tracking_id")
    version: str = Field("", serialization_alias="cmip6:version")
    product: str = Field(..., serialization_alias="cmip6:product")
    license: str = Field(..., serialization_alias="cmip6:license")
    grid: str = Field(..., serialization_alias="cmip6:grid")
    mip_era: str = Field(..., serialization_alias="cmip6:mip_era")

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


def make_cmip6_item_id(attrs: MutableMapping[str, Any]) -> str:
    """Return a unique ID for CMIP6 data item."""
    keys = [
        "activity_id",
        "institution_id",
        "source_id",
        "experiment_id",
        "variant_label",
        "table_id",
        "variable_id",
        "grid_label",
    ]
    name = "_".join(attrs[k] for k in keys)
    return name
    return hashlib.md5(name.encode("utf-8")).hexdigest()


class CMIP6populator(STACpopulatorBase):
    def __init__(self, stac_host: str, thredds_catalog_url: str, config_filename: str) -> None:
        """Constructor

        :param stac_host: URL to the STAC API
        :type stac_host: str
        :param thredds_catalog_url: the URL to the THREDDS catalog to ingest
        :type thredds_catalog_url: str
        :param config_filename: Yaml file containing the information about the collection to populate
        :type config_filename: str
        """

        data_loader = THREDDSLoader(thredds_catalog_url)
        self.props_model = Properties
        super().__init__(stac_host, data_loader, config_filename)

    def handle_ingestion_error(self, error: str, item_name: str, item_data: MutableMapping[str, Any]):
        pass

    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        """Creates the STAC item.

        :param item_name: name of the STAC item. Interpretation of name is left to the input loader implementation
        :type item_name: str
        :param item_data: dictionary like representation of all information on the item
        :type item_data: MutableMapping[str, Any]
        :return: _description_
        :rtype: MutableMapping[str, Any]
        """
        iid = make_cmip6_item_id(item_data["attributes"])

        obj = CFJsonItem(iid, item_data, self.props_model)

        # Add CMIP6 extension
        try:
            cmip6_ext = cmip6.CMIP6Extension.ext(obj.item, add_if_missing=True)
            cmip6_ext.apply(item_data["attributes"])
        except:
            LOGGER.warning(f"Failed to add CMIP6 extension to item {item_name}")

        # Add datacube extension
        try:
            dc_ext = DatacubeExtension.ext(obj.item, add_if_missing=True)
            dc_ext.apply(dimensions=obj.dimensions(), variables=obj.variables())
        except:
            LOGGER.warning(f"Failed to add Datacube extension to item {item_name}")

        return obj.item.to_dict()

    def validate_stac_item_cv(self, data: MutableMapping[str, Any]) -> bool:
        # Validation is done at the item creating stage, using the Properties class.
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="CMIP6 STAC populator")
    parser.add_argument("stac_host", type=str, help="STAC API address")
    parser.add_argument("thredds_catalog_URL", type=str, help="URL to the CMIP6 THREDDS catalog")
    parser.add_argument("config_file", type=str, help="Name of the configuration file")

    args = parser.parse_args()
    LOGGER.info(f"Arguments to call: {args}")
    c = CMIP6populator(args.stac_host, args.thredds_catalog_URL, args.config_file)
    c.ingest()
