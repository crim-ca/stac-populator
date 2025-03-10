from __future__ import annotations

from typing import Literal
from STACpopulator.extensions.base import ExtensionHelper


class Xscen(ExtensionHelper):
    type: Literal["forecast", "station-obs", "gridded-obs", "reconstruction", "simulation"]
    processing_level: Literal["raw", "extracted", "regridded", "biasadjusted"]
    license_type: Literal["permissive", "permissive non-commercial"]
    _prefix: str = "xscen"
