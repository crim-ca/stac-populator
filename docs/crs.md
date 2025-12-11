# Coordinate Reference System (CRS)

STAC bounding boxes and geometries require that values be described by the
[WGS84][wgs84] datum. However, the input metadata may describe coordinates
using other systems. In order to correctly translate the coordinates to [WGS84][wgs84] compliant values,
STAC populator must know what is the CRS of the original values.

STAC populator will transform the coordinates from the specified CRS to [EPSG:4326][epsg4326]
(for 2D coordinates) or [EPSG:4979][epsg4979] (for 3D coordinates) when creating bounding boxes and
geometries for STAC Items and Collections. Both of these CRSs are compliant with the STAC specification.

When running a populator implementation, the STAC populator assumes that the metadata from the files will specify
which CRS is used to represent the geospatial coordinates in the data.

For example, The `THREDDSPopulator` parses metadata from NCML metadata and looks for values named
`geospatial_bounds_crs` (and optionally `geospatial_bounds_crs_vertical`) to determine the CRS.

If these values are not specified then the CRS is unknown and STAC populator will not know how to transform the
geospatial coordinates to a CRS that STAC accepts.

If nothing is specified, then STAC populator will assume that the CRS is [EPSG:4326][epsg4326]
(for 2D coordinates) or [EPSG:4979][epsg4979] (for 3D coordinates).

To specify a different fallback CRS then use the `--fallback-crs` command line option. If you think that the CRS
specified in the metadata is incorrect and want to force STAC populator to use a different CRS even if one is
specified, use the `--force-crs` option instead.

The following precedence order is followed when STAC populator chooses which CRS to use:

1. CRS specified by `--force-crs` command line option
2. CRS specified in the metadata file being converted to a STAC item
3. CRS specified by the `--fallback-crs` command line option
4. [EPSG:4326][epsg4326] (for 2D coordinates) or [EPSG:4979][epsg4979] (for 3D coordinates)

Note that STAC populator will only transform coordinates to [WGS84][wgs84] compliant values when required by the
STAC specification. Other STAC extensions are free to represent the coordinates in any way they want.
For example, the [datacube extension][datacube] extension allows coordinates to be represented in any CRS so
STAC populator will not attempt to transform these coordinates for the `cube:dimensions` property.

## Useful CRS representations

### WGS84 but with longitude from 0-360 degrees

If your data contains longitude values from [0, 360] degrees instead of [-180, 180] (as required by [WGS84][wgs84]) you
can use the following CRS that is identical to [EPSG:4979][epsg4979] except that the prime meridian is shifted.
This means that longitude values between [0, 360] are properly transformed to the [-180, 180] range when transformed to
a [WGS84][wgs84] compliant CRS.

```text
GEOGCRS["WGS 84",
    DATUM["based on WGS 84 ellipsoid", ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]]],
    PRIMEM["Greenwich",-360,ANGLEUNIT["degree",0.0174532925199433]],
    CS[ellipsoidal,3],
    AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433]],
    AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433]],
    AXIS["ellipsoidal height (h)",up,ORDER[3],LENGTHUNIT["metre",1]]]
```

Note that the biggest difference between this and [EPSG:4979][epsg4979] is the section: `PRIMEM["Greenwich",-360`.

### EPSG:4979 or EPSG:4326 but with longitude and axes switched

If your data represents coordinates with longitude on the x axis and latitude on the y axis you can use
[OGC:CRS84h][ogccrs84h] which is similar to [EPSG:4979][epsg4979] except that the first two axes are swapped or
[OGC:CRS84][ogccrs84] which is similar to [EPSG:4326][epsg4326] except that the first two axes are swapped.

<!-- TODO: add more examples here as they come up -->

[epsg4326]: https://epsg.io/4326
[epsg4979]: https://epsg.io/4979
[wgs84]: https://www.opengis.net/def/crs/OGC/1.3/CRS84
[ogccrs84h]: https://spatialreference.org/ref/ogc/CRS84h/
[ogccrs84]: https://spatialreference.org/ref/ogc/CRS84/
[datacube]: https://stac-extensions.github.io/datacube/v2.3.0/schema.json
