from __future__ import annotations

from STACpopulator.extensions.rdps import RDPSDataModel


# Customize the THREDDSCatalogDataModel
class HRDPSDataModel(RDPSDataModel):
    """Data model for HRDPS NetCDF datasets."""

    # FIXME: No specific props beyond RPDS. Maybe delete and only keep the RDPS impl.?
    pass
