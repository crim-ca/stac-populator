import argparse
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, MutableMapping

import pyessv
from colorlog import ColoredFormatter
from pydantic import AnyHttpUrl, BaseModel, Field, FieldValidationInfo, field_validator
from typing_extensions import TypedDict

from STACpopulator import STACpopulatorBase
from STACpopulator.input import THREDDSLoader
from STACpopulator.stac_utils import collection2enum

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
ActivityID = collection2enum(CV.activity_id)
ExperimentID = collection2enum(CV.experiment_id)
Frequency = collection2enum(CV.frequency)
GridLabel = collection2enum(CV.grid_label)
InstitutionID = collection2enum(CV.institution_id)
# Member = collection2enum(CV.member_id)  # This is empty
NominalResolution = collection2enum(CV.nominal_resolution)
Realm = collection2enum(CV.realm)
SourceID = collection2enum(CV.source_id)
SourceType = collection2enum(CV.source_type)
SubExperimentID = collection2enum(CV.sub_experiment_id)
TableID = collection2enum(CV.table_id)
# Variable = collection2enum(CV.variable_id)  # This is empty


class STACAsset(BaseModel):
    href: AnyHttpUrl
    media_type: str
    title: str
    roles: List[str]


class Properties(BaseModel, validate_assignment=True):
    """Data model for CMIP6 Controlled Vocabulary."""

    start_datetime: datetime
    end_datetime: datetime
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
    version: str = Field(..., serialization_alias="cmip6:version")
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


class Geometry(TypedDict):
    type: str
    coordinates: List[List[List[float]]]


class STACItem(BaseModel):
    id: str
    geometry: Geometry
    bbox: List[float]
    properties: Properties
    assets: Dict[str, STACAsset]


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
    return "_".join(attrs[k] for k in keys)


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

        attrs = item_data["attributes"]
        meta = item_data["groups"]["CFMetadata"]["attributes"]

        props = Properties(
            attrs,
            start_datetime=meta["time_coverage_start"],
            end_datetime=meta["time_coverage_end"],
        )

        a = STACAsset(
            href=item_data["access_urls"]["HTTPServer"],
            media_type="application/netcdf",
            title="HTTP Server",
            roles=["data"],
        )

        item = STACItem(
            id="sdfdd",
            properties=props,
            geometry=THREDDSLoader.ncattrs_to_geometry(meta),
            bbox=THREDDSLoader.ncattrs_to_bbox(meta),
            assets={"http": a},
        )

        stac_item_json = json.loads(item.model_dump_json(by_alias=True))

        return stac_item_json

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
    # c.ingest()
