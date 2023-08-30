import argparse
import datetime as dt
import logging
from typing import Any, List, Literal, MutableMapping

import pyessv
import pystac
from colorlog import ColoredFormatter
from pydantic import (
    BaseModel,
    Field,
    FieldValidationInfo,
    ValidationError,
    field_validator,
)

from STACpopulator import STACpopulatorBase
from STACpopulator.input import THREDDSLoader

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
Activity = collection2enum(CV.activity_id)
Experiment = collection2enum(CV.experiment_id)
Frequency = collection2enum(CV.frequency)
GridLabel = collection2enum(CV.grid_label)
Institution = collection2enum(CV.institution_id)
# Member = collection2enum(CV.member_id)  # This is empty
Resolution = collection2enum(CV.nominal_resolution)
Realm = collection2enum(CV.realm)
Source = collection2enum(CV.source_id)
SourceType = collection2enum(CV.source_type)
SubExperiment = collection2enum(CV.sub_experiment_id)
Table = collection2enum(CV.table_id)
Variable = collection2enum(CV.variable_id)  # This is empty


class Properties(BaseModel):
    """Data model for CMIP6 Controlled Vocabulary."""

    activity: Activity = Field(..., alias="activity_id")
    experiment: Experiment = Field(..., alias="experiment_id")
    frequency: Frequency
    grid_label: GridLabel
    institution: Institution = Field(..., alias="institution_id")
    resolution: Resolution = Field(..., alias="nominal_resolution")
    realm: List[Realm] = Field(..., alias="realm")
    source: Source = Field(..., alias="source_id")
    source_type: List[SourceType] = Field(..., alias="source_type")
    sub_experiment: SubExperiment | Literal["none"] = Field(..., alias="sub_experiment_id")
    table: Table = Field(..., alias="table_id")
    variable: Variable = str  # Field(..., alias="variable_id")
    variant_label: str
    initialization_index: int
    physics_index: int
    realization_index: int
    forcing_index: int
    variant_label: str
    tracking_id: str
    version: str = None
    license: str = None
    grid: str = None

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


class STACItem(BaseModel):
    start_datetime: dt.datetime
    end_datetime: dt.datetime


def make_cmip6_id(attrs: MutableMapping[str, Any]) -> str:
    """Return unique ID for CMIP6 data collection (multiple variables)."""
    keys = [
        "activity_id",
        "institution_id",
        "source_id",
        "experiment_id",
        "variant_label",
        "table_id",
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

        for name, item in data_loader:
            # self.create_stac_item(name, item)
            print(name)
        super().__init__(stac_host, data_loader, config_filename)

    def handle_ingestion_error(self, error: str, item_name: str, item_data: MutableMapping[str, Any]):
        pass

    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        # TODO: next step is to implement this
        attrs = item_data["attributes"]
        meta = item_data["groups"]["CFMetadata"]["attributes"]

        # Create STAC item geometry from CFMetadata
        item = dict(
            id=make_cmip6_id(attrs),
            geometry=THREDDSLoader.ncattrs_to_geometry(meta),
            bbox=THREDDSLoader.ncattrs_to_bbox(meta),
            properties=Properties(**attrs).model_dump(),
            datetime=None,
        )

        item.update(
            STACItem(
                start_datetime=meta["time_coverage_start"],
                end_datetime=meta["time_coverage_end"],
            ).model_dump()
        )

        return pystac.Item(**item)

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
