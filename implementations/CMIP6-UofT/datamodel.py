"""
Data model for the attributes of a collection.
"""
# TODO: Make this data model compatible with STAC Items and Collections.

from pydantic import BaseModel, HttpUrl, constr, validator, Field, field_validator
import datetime as dt
from typing import Literal, Optional, Dict
from collections import OrderedDict
import pyessv
from enum import Enum


def collection2enum(collection):
    """Create Enum based on terms from pyessv collection.

    Parameters
    ----------
    collection : pyessv.model.collection.Collection
      pyessv collection of terms.

    Returns
    -------
    Enum
      Enum storing terms and their labels from collection.
    """
    mp = {term.name: term.label for term in collection}
    return Enum(collection.raw_name.capitalize(), mp, module="base")


# CMIP6 controlled vocabulary (CV)
CV = pyessv.WCRP.CMIP6

# Enum classes built from the pyessv' CV
Activity = collection2enum(CV.activity_id)
Experiment = collection2enum(CV.experiment_id)
Frequency = collection2enum(CV.frequency)
GridLabel = collection2enum(CV.grid_label)
Institute = collection2enum(CV.institution_id)
Member = collection2enum(CV.member_id)
Resolution = collection2enum(CV.nominal_resolution)
Realm = collection2enum(CV.realm)
Source = collection2enum(CV.source_id)
SourceType = collection2enum(CV.source_type)
SubExperiment = collection2enum(CV.sub_experiment_id)
Table = collection2enum(CV.table_id)
Variable = collection2enum(CV.variable_id)


class Attributes(BaseModel):
    """Should be extended for each collection."""
    path_: HttpUrl
    date_start: dt.datetime
    date_end: dt.datetime
    version: str = None
    license: str = None


class CMIP6Attributes(Attributes):
    """Data model for catalog entries for CMIP5 simulations.
    """
    activity: Activity = Field(..., alias="activity_id")
    experiment: Experiment = Field(..., alias="experiment_id")
    frequency: Frequency
    grid_label: GridLabel
    institute: Institute = Field(..., alias="institute_id")
    member: Member = Field(..., alias="member_id")
    resolution: Resolution = Field(..., alias="nominal_resolution")
    realm: Realm = Field(..., alias="realm")
    source: Source = Field(..., alias="source_id")
    source_type: SourceType = Field(..., alias="source_type")
    sub_experiment: SubExperiment = Field(..., alias="sub_experiment_id")
    table: Table = Field(..., alias="table_id")
    variable: Variable = Field(..., alias="variable_id")



class CatalogEntry(BaseModel):
    attributes: Attributes
    variables: Dict[str, CFVariable]

    def __init__(self, **kwargs):
        # Copy attributes that are deeply nested within groups.
        if "THREDDSMetadata" in kwargs["groups"]:
            kwargs["attributes"]["path_"] = kwargs["groups"]["THREDDSMetadata"]["groups"]["services"]["attributes"]["opendap_service"]
            kwargs["attributes"]["date_start"] = kwargs["groups"]["CFMetadata"]["attributes"][
                "time_coverage_start"]
            kwargs["attributes"]["date_end"] = kwargs["groups"]["CFMetadata"]["attributes"]["time_coverage_end"]
        else:
            kwargs["attributes"]["path_"] = kwargs["@location"]

        # Ingest data variables only.
        variables = OrderedDict()
        bounds = [v.get("attributes", {}).get("bounds") for v in kwargs["variables"].values()]

        for name, var in kwargs["variables"].items():
            # Select data variables only
            if ('_CoordinateAxisType' not in var.get("attributes", {}) and
                    name not in var["shape"] and
                    name not in bounds):
                variables[name] = var
                variables[name]["name"] = name

        kwargs["variables"] = variables

        super().__init__(**kwargs)
