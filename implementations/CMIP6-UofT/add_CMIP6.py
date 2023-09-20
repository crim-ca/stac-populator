import argparse
import logging
from typing import Any, MutableMapping, Literal, List
import datetime as dt
import hashlib

from colorlog import ColoredFormatter
import pystac
from pydantic import BaseModel, Field, FieldValidationInfo, field_validator, ValidationError
from STACpopulator import STACpopulatorBase
from STACpopulator.input import THREDDSLoader
from STACpopulator.stac_utils import collection2literal
import pyessv


media_types = {"httpserver_service": "application/x-netcdf",
               "opendap_service": pystac.MediaType.HTML,
               "wcs_service": pystac.MediaType.XML,
               "wms_service": pystac.MediaType.XML,
               "nccs_service": "application/x-netcdf",
               "HTTPServer": "application/x-netcdf",
               "OPENDAP": pystac.MediaType.HTML,
               "NCML": pystac.MediaType.XML,
               "WCS": pystac.MediaType.XML,
               "ISO": pystac.MediaType.XML,
               "WMS": pystac.MediaType.XML,
               "NetcdfSubset": "application/x-netcdf",
               }

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
Activity = collection2literal(CV.activity_id)
Experiment = collection2literal(CV.experiment_id)
Frequency = collection2literal(CV.frequency)
GridLabel = collection2literal(CV.grid_label)
Institution = collection2literal(CV.institution_id)
# Member = collection2literal(CV.member_id)  # This is empty
Resolution = collection2literal(CV.nominal_resolution)
Realm = collection2literal(CV.realm)
Source = collection2literal(CV.source_id)
SourceType = collection2literal(CV.source_type)
SubExperiment = collection2literal(CV.sub_experiment_id)
Table = collection2literal(CV.table_id)
# Variable = collection2literal(CV.variable_id)  # This is empty


class Properties(BaseModel):
    """Data model for CMIP6 Controlled Vocabulary.
    """
    activity: Activity = Field(..., alias="activity_id")
    experiment: Experiment = Field(..., alias="experiment_id")
    frequency: Frequency
    grid_label: GridLabel
    institution: Institution = Field(..., alias="institution_id")
    resolution: Resolution = Field(..., alias="nominal_resolution")
    realm: List[Realm] = Field(..., alias="realm")
    source: Source = Field(..., alias="source_id")
    source_type: List[SourceType] = Field(..., alias="source_type")
    sub_experiment: SubExperiment | Literal['none'] = Field(..., alias="sub_experiment_id")
    table: Table = Field(..., alias="table_id")
    # variable: str  # Field(..., alias="variable_id")
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
    keys = ["activity_id", "institution_id", "source_id", "experiment_id", "variant_label", "table_id", "grid_label",]
    item_name = "_".join(attrs[k] for k in keys)
    return hashlib.md5(item_name.encode("utf-8")).hexdigest()


class CMIP6populator(STACpopulatorBase):
    def __init__(
            self,
            stac_host: str,
            thredds_catalog_url: str,
            config_filename: str,
            validator: callable = None
    ) -> None:
        """Constructor

        :param stac_host: URL to the STAC API
        :type stac_host: str
        :param thredds_catalog_url: the URL to the THREDDS catalog to ingest
        :type thredds_catalog_url: str
        :param config_filename: Yaml file containing the information about the collection to populate
        :type config_filename: str
        :param: validator: a function that validates and returns a dictionary of attributes.
        """

        data_loader = THREDDSLoader(thredds_catalog_url)
        self.validator = validator

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

        # uuid
        # Create STAC item geometry from CFMetadata
        item = dict(
            id=make_cmip6_id(attrs),
            geometry=THREDDSLoader.ncattrs_to_geometry(meta),
            bbox=THREDDSLoader.ncattrs_to_bbox(meta),
            properties=Properties(**attrs).model_dump(),
            datetime=None,
        )

        item.update(STACItem(start_datetime=meta["time_coverage_start"],
            end_datetime=meta["time_coverage_end"],).model_dump())

        stac_item = pystac.Item(**item)

        # Add assets
        for name, url in item_data["access_urls"].items():
            asset = pystac.Asset(href=url, media_type=media_types.get(name, None))
            stac_item.add_asset(name, asset)

        return stac_item.to_dict()

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
