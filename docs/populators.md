# Adding New and Custom Implementations

This documentation describes how to create a new STAC populator implementation.

This tutorial uses the `RDPSpopulator` implementation as an example which integrates data properties from a THREDDS Catalog. The process of integrating data from other sources is similar.

## Resources

- [PySTAC Docs](https://pystac.readthedocs.io/en/stable/)
- [STAC Extensions](https://stac-extensions.github.io/)
- [STAC API](https://github.com/radiantearth/stac-api-spec)
- [THREDDS Catalog](https://docs.unidata.ucar.edu/tds/current/userguide/)


## Implementing a new populator

A `STAC populator` implementation extracts data from a source (e.g., a THREDDS Catalog) and processes it into STAC Items and Collections before uploading them to a STAC API instance. It uses STAC Extensions to describe the structure of the Item and Collection properties.

An implementation integrates several python classes that each handle metadata extraction, processing, integration, and upload. The following sections describe each class's purpose and implementation: `Extensions`, `Helpers`, `Data Model`, and `Populator`.

## 1. Extensions

An extension defines methods to extend STAC items and collections with additional relevant attributes describing specific properties of the dataset. For instance, the [`FileExtension`](https://github.com/stac-utils/pystac/blob/main/pystac/extensions/file.py) defines attributes that can be extracted from [`Asset`](https://pystac.readthedocs.io/en/stable/api/asset.html) and [`Link`](https://pystac.readthedocs.io/en/stable/api/item.html) objects to describe the associated files. 

Be aware that there are different [levels of extension maturity](https://github.com/radiantearth/stac-spec/blob/master/extensions/README.md#extension-maturity) in the STAC ecosystem. Typically, an existing extension has at least a clear specification such as [this one](https://github.com/stac-extensions/file) for the `FileExtension`. An extension maturity can go as far as being integrated into a stable version of the [pystac](https://github.com/stac-utils/pystac/tree/main) Python library. For instance, `FileExtension` is available in `pystac`, while `ContactExtension` specified [here](https://github.com/stac-extensions/contacts) in not yet included in `pystac` as of version 1.14.1.

It is therefore still common to manually implement certain extensions based on their official specifications and the [PySTAC guidelines](https://pystac.readthedocs.io/en/latest/tutorials/adding-new-and-custom-extensions.html). In such a case, we recommend adding the new extension implementation under the `STACpopulator/extensions/` directory, and then submitting a pull request (PR) to the `pystac` repository for its official integration.

In summary, it is essential to identify all relevant extensions that need to be applied in the new `stac-populator` implementation. For example, our `RDPS Implementation` makes use of the `DataCubeExtension`, `FileExtension`, and `CFExtension` on the item/asset level, and of the `ContactExtension` on the collection level. Collection-level extensions are specifically discussed in [Section 5](#5-collection-level-extensions).

## 2. Helpers

In `stac-populator`, an extension is typically applied using an associated helper. A helper extends the [`Helper`](../STACpopulator/extensions/base.py#L64) abstract class and implements methods for retrieving or computing the data properties to be applied by the extension. For convenience an [`ExtensionHelper`]((../STACpopulator/extensions/base.py#L78)) class extends both `Helper` and the pydantic `BaseModel` classes to provide default constructor and validation mechanisms for defined attributes. 

**A concrete helper** should extend `ExtensionHelper` and implement the following:

1. Define property methods typically annotated with `@functools.cached_property`.
2. Redefine as needed the `def apply(...)` method where data properties are applied using the corresponding STAC extension.
3. Implement a `def from_data(...)` method to enable static initialization of the helper with extra kwargs.

The example below shows an excerpt of the concrete `FileHelper` class. In addition to the required `data` field to compute the file `size` property, additional keyword arguments such as the http `session` can be passed in for initialization through `from_data(..., **kwargs)`. In particular, this static method facilitates instantiation of helpers at the next layer, i.e. in the `DataModel` associated with the populator implementation.

```python
import pystac
import functools
from requests import Session
from pydantic import Field, Any
from pystac.extensions.file import FileExtension

from STACpopulator.extensions.base import ExtensionHelper


class FileHelper(ExtensionHelper):
    access_urls: dict[str, str]
    ...
    session: Optional[Session] = Field(default=None, exclude=True)

    @classmethod
    def from_data(
        cls,
        data: dict[str, Any],
        **kwargs,
    ) -> "FileHelper":
        """Create a FileHelper instance from raw data."""
        return cls(access_urls=data["data"]["access_urls"], **kwargs)

    def apply(self, item: pystac.Item, add_if_missing: bool = True) -> T:
        asset = item.assets[...]
        file_ext = FileExtension.ext(asset, add_if_missing=add_if_missing)
        file_ext.apply(
            size=self.size,
            ...
        )

    @functools.cached_property
    def size(self) -> Optional[int]:
        """Return file size in bytes, None if an error occurs."""
        size: int = ... # Code logic to calculate the file size
        return size
```

## 3. Data Model

Inheriting from [`BaseSTAC`](../STACpopulator/extensions/base.py#L159), a `DataModel` is the main data management class associated with an implementation in `stac-populator`. It holds `helper` objects as attributes, which it uses to apply multiple extensions to a given entity (i.e., `item`, `asset`, `link`, or `collection`).

In `stac-populator` the [`THREDDSCatalogDataModel`](../STACpopulator/extensions/thredds.py#L173) class defines the minimal data model to preprocess and integrate data properties from a THREDDS Catalog. This catalog data model class includes the [`THREDDSHelper`](../STACpopulator/extensions/thredds.py#L133) used to add generic thredds properties from the catalog (e.g., `links`, `services`), and the [`DataCubeHelper`](../STACpopulator/extensions/datacube.py#L13) to add data cube-related properties (e.g., `dimensions`, `variables`, `bounds`).

**A custom THREDDS data model class** must extend the `THREDDSCatalogDataModel` and only needs to define the additional helpers it should use. 

Data model instances should be created using the `def from_data(...)` factory method, which accepts extra keyword arguments that are forwarded to the helper constructors. During instantiation, the data model automatically initializes its `helper` attributes by calling each helper’s own `def from_data(...)` method. The keyword arguments are distributed among the helpers based on their constructor signatures, allowing the data model to accept all required parameters in one place and dispatch them efficiently. The instantiated helpers are later automatically applied to extend the data model before integrating the data properties.


The example below shows the `RDPSDataModel`. In addition to the default `THREDDSHelper` and `DataCubeHelper` inherited from `THREDDSCatalogDataModel`, this data model defines the `CFHelper` and the `FileHelper`, which respectively apply the `CFExtension` and `FileExtension`.


```python
from STACpopulator.extensions.cf import CFHelper
from STACpopulator.extensions.file import FileHelper
from STACpopulator.extensions.thredds import THREDDSCatalogDataModel


class RDPSDataModel(THREDDSCatalogDataModel):
    """Data model for RDPS NetCDF datasets."""

    cf: CFHelper
    file: FileHelper
```

## 4. Populator

Populators are defined in a specific directory created under `STACpopulator/implementations/`, to which we will refer in the following as the populator's package. To maintain consistency, the name of this newly created directory should follow the naming convention: `STACpopulator/implementations/IMPLEMENTATION_AUTHOR/`. 

For instance, we create `STACpopulator/implementations/RDPS_CRIM/` for the RDPS populator, with `RDPS_CRIM` being the package name.

### 4.1. Creating the populator class

A populator class inherits from the [`STACpopulatorBase`](../STACpopulator/populator_base.py#L26) abstract class and represents the final data layer in a `stac-populator` implementation. It must specify the corresponding `DataModel` type and implement the abstract method `create_stac_item(...)`, which creates a data model instance for each STAC item while applying the relevant extensions described earlier. A populator class also inherits the `def ingest(...)` method, which is called when the command associated with the populator implementation is executed, triggering the data ingestion process.

The example below shows the [`RDPSpopulator`](../STACpopulator/implementations/RDPS_CRIM/add_RDPS.py#L14) class. 


```python
from typing import Any

from STACpopulator.extensions.rdps import RDPSDataModel
from STACpopulator.populator_base import STACpopulatorBase


class RDPSpopulator(STACpopulatorBase):
    """Populator that creates STAC objects representing RDPS data from a THREDDS catalog."""

    data_model = RDPSDataModel

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Return a STAC item."""
        model = self.data_model.from_data(item_data, session=self._session)
        return model.stac_item()
```

### 4.2. Adding populator CLI command

To be able to invoke the populator from the CLI, following updates must be performed.

1. Copy the `def add_parser_args(...)` and `def runner(...)` methods from the [`STACpopulator/implementations/RDPS_CRIM/add_RDPS.py`](../STACpopulator/implementations/RDPS_CRIM/add_RDPS.py) file.
2. Update the Python docstrings and CLI help strings to reflect the new populator’s name and specific behavior.
3. Export these methods in the `__init__.py` file of the populator's directory. 

For instance, in `STACpopulator/implementations/RDPS_CRIM/__init__.py` for the RDPS populator.

```python
from .add_RDPS import add_parser_args, runner

__all__ = ["add_parser_args", "runner"]
```

4. Register the new populator implementation in [`STACpopulator/implementations/__init__.py`](../STACpopulator/implementations/__init__.py)

```python
__all__ = [..., "RDPS_CRIM", "IMPLEMENTATION_AUTHOR"]
# Replace IMPLEMENTATION_AUTHOR with the name of your new implementation's package name
```


## 5. Collection-level Extensions

Collection-level extensions are currently specified in a `collection_config.yml` file under the populator’s directory. This file defines general metadata associated with the collection, including fields such as `name`, `keywords`, `license`, `providers`, etc. For an example, refer to the [`RDPS_CRIM/collection_config.yml`](../STACpopulator/implementations/RDPS_CRIM/collection_config.yml) file in the RDPS implementation.

🚨 **Important**

Note that programatic integration of collection-level extensions (similar to how item extensions are handled) is currently under active development and will be available soon.