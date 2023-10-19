import argparse
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, MutableMapping, Optional

import pyessv
from colorlog import ColoredFormatter
from extensions import DataCubeHelper
from pydantic import AnyHttpUrl, ConfigDict, Field, FieldValidationInfo, field_validator

from STACpopulator import STACpopulatorBase
from STACpopulator.input import THREDDSLoader
from STACpopulator.models import GeoJSONPolygon, STACItemProperties
from STACpopulator.stac_utils import STAC_item_from_metadata, collection2literal

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
NominalResolution = collection2literal(CV.nominal_resolution)
Realm = collection2literal(CV.realm)
SourceID = collection2literal(CV.source_id)
SourceType = collection2literal(CV.source_type)
SubExperimentID = collection2literal(CV.sub_experiment_id)
TableID = collection2literal(CV.table_id)


def add_cmip6_prefix(name: str) -> str:
    return "cmip6:" + name if "datetime" not in name else name


class CMIP6ItemProperties(STACItemProperties, validate_assignment=True):
    """Data model for CMIP6 Controlled Vocabulary."""

    Conventions: str
    activity_id: ActivityID
    creation_date: datetime
    data_specs_version: str
    experiment: str
    experiment_id: ExperimentID
    frequency: Frequency
    further_info_url: AnyHttpUrl
    grid_label: GridLabel
    institution: str
    institution_id: InstitutionID
    nominal_resolution: NominalResolution
    realm: List[Realm]
    source: str
    source_id: SourceID
    source_type: List[SourceType]
    sub_experiment: str | Literal["none"]
    sub_experiment_id: SubExperimentID | Literal["none"]
    table_id: TableID
    variable_id: str
    variant_label: str
    initialization_index: int
    physics_index: int
    realization_index: int
    forcing_index: int
    tracking_id: str
    version: str = Field("")
    product: str
    license: str
    grid: str
    mip_era: str

    model_config = ConfigDict(alias_generator=add_cmip6_prefix, populate_by_name=True)

    @field_validator("initialization_index", "physics_index", "realization_index", "forcing_index", mode="before")
    @classmethod
    def only_item(cls, v: list[int], info: FieldValidationInfo):
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


class CMIP6populator(STACpopulatorBase):
    item_properties_model = CMIP6ItemProperties
    item_geometry_model = GeoJSONPolygon

    def __init__(self, stac_host: str, thredds_catalog_url: str, update: Optional[bool] = False) -> None:
        """Constructor

        :param stac_host: URL to the STAC API
        :type stac_host: str
        :param thredds_catalog_url: the URL to the THREDDS catalog to ingest
        :type thredds_catalog_url: str
        """
        data_loader = THREDDSLoader(thredds_catalog_url)

        super().__init__(stac_host, data_loader, update)

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

        item = STAC_item_from_metadata(iid, item_data, self.item_properties_model, self.item_geometry_model)

        # Add datacube extension
        try:
            dchelper = DataCubeHelper(item_data)
            dc_ext = DatacubeExtension.ext(item, add_if_missing=True)
            dc_ext.apply(dimensions=dchelper.dimensions(), variables=dchelper.variables())
        except:
            LOGGER.warning(f"Failed to add Datacube extension to item {item_name}")

        # print(json.dumps(item.to_dict()))
        return json.loads(json.dumps(item.to_dict()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="CMIP6 STAC populator")
    parser.add_argument("stac_host", type=str, help="STAC API address")
    parser.add_argument("thredds_catalog_URL", type=str, help="URL to the CMIP6 THREDDS catalog")
    parser.add_argument("--update", action="store_true", help="Update collection and its items")

    args = parser.parse_args()

    LOGGER.info(f"Arguments to call: {args}")
    c = CMIP6populator(args.stac_host, args.thredds_catalog_URL, args.update)
    c.ingest()
