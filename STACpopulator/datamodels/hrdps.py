from STACpopulator.datamodels.rdps import RDPSDataModel


# Customize the THREDDSCatalogDataModel
class HRDPSDataModel(RDPSDataModel):
    """Data model for HRDPS NetCDF datasets."""

    # FIXME: No specific props beyond RPDS. Kept to facilitate evolution.
    pass
