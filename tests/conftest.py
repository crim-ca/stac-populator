import pytest


@pytest.fixture
def epsg4979_0_360_wkt():
    return """
    GEOGCRS["WGS 84",
        DATUM[
            "based on WGS 84 ellipsoid",
            ELLIPSOID[
                "WGS 84",
                6378137,
                298.257223563,
                LENGTHUNIT["metre",1]
            ]
        ],
        PRIMEM[
            "Greenwich",
            -360,
            ANGLEUNIT[
                "degree",
                0.0174532925199433
            ]
        ],
        CS[
            ellipsoidal,
            3
        ],
        AXIS[
            "geodetic longitude (Lon)",
            east,
            ORDER[1],
            ANGLEUNIT[
                "degree",
                0.0174532925199433
            ]
        ],
        AXIS[
            "geodetic latitude (Lat)",
            north,
            ORDER[2],
            ANGLEUNIT[
                "degree",
                0.0174532925199433
            ]
        ],
        AXIS[
            "ellipsoidal height (h)",
            up,
            ORDER[3],
            LENGTHUNIT["metre",1]
        ]
    ]
    """
