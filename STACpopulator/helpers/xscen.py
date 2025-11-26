from __future__ import annotations

from typing import Literal

from STACpopulator.helpers.base import ExtensionHelper


class Xscen(ExtensionHelper):
    """
    XSCEN extension helper class.

    See: https://github.com/Ouranosinc/xscen
    """

    type: Literal["forecast", "station-obs", "gridded-obs", "reconstruction", "simulation"]
    processing_level: Literal["raw", "extracted", "regridded", "biasadjusted"]
    license_type: Literal["permissive", "permissive non-commercial"]
    _prefix: str = "xscen"
