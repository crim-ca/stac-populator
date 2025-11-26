from __future__ import annotations

import inspect

from pydantic import ConfigDict, model_validator

from STACpopulator.datamodels.base import BaseSTAC
from STACpopulator.helpers.base import Helper
from STACpopulator.helpers.datacube import DataCubeHelper
from STACpopulator.helpers.thredds import THREDDSHelper
from STACpopulator.stac_utils import ncattrs_to_bbox, ncattrs_to_geometry


class THREDDSCatalogDataModel(BaseSTAC):
    """Base class ingesting attributes loaded by `THREDDSLoader` and creating a STAC item.

    This is meant to be subclassed for each extension.

    It includes two validation mechanisms:
     - pydantic validation using type hints, and
     - json schema validation.
    """

    # Data from loader
    data: dict

    # Extensions classes
    datacube: DataCubeHelper
    thredds: THREDDSHelper

    model_config = ConfigDict(populate_by_name=True, extra="ignore", arbitrary_types_allowed=True)

    @classmethod
    def from_data(cls, data: dict, **kwargs) -> THREDDSCatalogDataModel:
        """
        Instantiate class from data provided by THREDDS Loader.

        This is where we match the Loader's output to the STAC item and extensions inputs. If we had multiple
        loaders, that's probably the only thing that would be different between them.
        """
        # Inject kwargs for helpers into data
        data["_extra_kwargs"] = kwargs

        return cls(
            data=data,
            start_datetime=data["groups"]["CFMetadata"]["attributes"]["time_coverage_start"],
            end_datetime=data["groups"]["CFMetadata"]["attributes"]["time_coverage_end"],
            geometry=ncattrs_to_geometry(data),
            bbox=ncattrs_to_bbox(data),
        )

    @model_validator(mode="before")
    @classmethod
    def instantiate_helpers(cls, data: dict[str, any]) -> dict[str, any]:
        """Automatically instantiate helper fields before model initialization.

        This method detects all fields annotated as subclasses of `Helper`
        and populates them by calling their respective `from_data()` constructors.
        Any extra keyword arguments are forwarded to helpers that accept them.

        Parameters
        ----------
        data : dict[str, Any]
            The raw input dictionary of parameters used to construct this class.

        Returns
        -------
        dict[str, Any]
            The modified data dictionary with instantiated helper objects injected
            into their corresponding fields.
        """
        # Retrieve forwarded kwargs and remove from the data object
        kwargs = data["data"].pop("_extra_kwargs", {})

        # Iterate over model fields and find helpers
        for field_name, field in cls.model_fields.items():
            field_type = field.annotation
            if isinstance(field_type, type) and issubclass(field_type, Helper):
                # if helper not provided in constructor
                if field_name not in data:
                    # Filter kwargs to only include those accepted by the helper's constructor.
                    type_signature = inspect.signature(field_type.__init__)
                    accepted_kwargs = {k: v for k, v in kwargs.items() if k in type_signature.parameters}
                    # Instantiate helper and forward accepted kwargs
                    data[field_name] = field_type.from_data(data, **accepted_kwargs)
        return data

    def create_uid(self) -> str:
        """Return a unique ID from the server location.

        For datasets with a DRS, it might might more sense to use the dataset's metadata instead.
        """
        if "HTTPServer" in self.data["access_urls"]:
            location = self.data["access_urls"]["HTTPServer"].split("/fileServer/")[1]
        elif "OpenDAP" in self.data["access_urls"]:
            location = self.data["access_urls"]["OPENDAP"].split("/dodsC/")[1]
        elif "NCML" in self.data["access_urls"]:
            location = self.data["access_urls"]["NCML"].split("/ncml/")[1]
        else:
            raise ValueError("No valid access URL found in data.")
        return location.replace("/", "__")
