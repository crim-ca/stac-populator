from STACpopulator.datamodels.thredds import THREDDSCatalogDataModel
from STACpopulator.helpers.cf import CFHelper
from STACpopulator.helpers.file import FileHelper


class RDPSDataModel(THREDDSCatalogDataModel):
    """Data model for RDPS NetCDF datasets."""

    # Extension classes
    cf: CFHelper
    file: FileHelper
