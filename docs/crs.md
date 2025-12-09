# Coordinate Reference System (CRS)

When running a populator implementation, the STAC populator assumes that the metadata from the files will specify
which CRS is used to represent the geospatial coordinates in the data.

For example, The `THREDDSPopulator` parses metadata from NCML metadata and looks for values named
`geospatial_bounds_crs` (and optionally `geospatial_bounds_crs_vertical`) to determine the CRS.

If these values are not specified then the CRS is unknown and STAC populator will not know how to convert the
geospatial coordinates to a CRS that STAC accepts. If nothing is specified, then STAC populator will assume
that the CRS is EPSG:4326 (for 2D coordinates) or EPSG:4979 (for 3D coordinates).

To specify a different fallback CRS then use the `--fallback-crs` command line option. If you think that the CRS
specified in the metadata is incorrect and want to force STAC populator to use a different CRS even if one is
specified, use the `--force-crs` option instead.

## Useful CRS representations

### WGS84 but with longitude from 0-360 degrees

If your data contains longitude values from 0-360 degrees instead of -180-180 (as required by WGS84) you can use the
following CRS that is identical to EPSG:4979 except that the prime meridian is shifted.
This means that longitude values between 0-360 are properly converted to WGS84 when transformed to a WGS84 compliant CRS.

```text
GEOGCRS["WGS 84",
    DATUM["based on WGS 84 ellipsoid", ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]]],
    PRIMEM["Greenwich",-360,ANGLEUNIT["degree",0.0174532925199433]],
    CS[ellipsoidal,3],
    AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],
    AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],
    AXIS["ellipsoidal height (h)",up,ORDER[3],LENGTHUNIT["metre",1]]]
```

Note that the biggest difference between this and EPSG:4979 is the section: `PRIMEM["Greenwich",-360`.

### WGS84 but with longitude and axes switched

If your data represents coordinates with longitude on the x axis and latitude on the y axis you can use the following
CRS that is identical to EPSG:4979 except that the first two axes are swapped.

```text
GEOGCRS["WGS 84",
    DATUM["based on WGS 84 ellipsoid",ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]]],
    PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],
    CS[ellipsoidal,3],
    AXIS["geodetic longitude (Lon)",east,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],
    AXIS["geodetic latitude (Lat)",north,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],
    AXIS["ellipsoidal height (h)",up,ORDER[3],LENGTHUNIT["metre",1]]]
```

Note the order of the `AXIS` sections.

<!-- TODO: add more examples here as they come up -->
