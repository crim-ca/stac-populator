# Adding New Implementations

This documentation describes how to create a new STAC populator implementation.

For illustration purpose, this tutorial shows the steps for implementing the `RDPSpopulator` which integrates data properties from a THREDDS Catalog. The process of integrating data from other sources is similar.

## Resources

- [PySTAC Docs](https://pystac.readthedocs.io/en/stable/)
- [STAC Extensions][stac-extensions]
- [STAC API][stac-api]
- [THREDDS Catalog](https://docs.unidata.ucar.edu/tds/current/userguide/)

## Implementing a new populator

A STAC `Populator` implementation extracts data from a source (e.g., a THREDDS Catalog) and processes it into STAC [`Item`][pystac-item] and [`Collection`][pystac-collection] objects before uploading them to a [`STAC API`][stac-api] instance. It uses [`STAC Extensions`][stac-extensions] to describe the structure of the [Item][pystac-item] and [Collection][pystac-collection] properties.

An implementation integrates several python classes that each handle metadata extraction, processing, integration, and upload. The following sections describe each class's purpose and implementation: `Extensions`, `Helpers`, `DataModel`, and `Populator`.

## 1. Extensions

An extension defines methods to extend STAC [Item][pystac-item] and [Collection][pystac-collection] objects with additional relevant attributes describing specific properties of the dataset. For instance, the [`FileExtension`][file-extension] defines attributes that can be extracted from [`Asset`][pystac-asset] and [`Link`][pystac-link] objects to describe the associated files.

Be aware that there are different [levels of extension maturity](https://github.com/radiantearth/stac-spec/blob/master/extensions/README.md#extension-maturity) in the STAC ecosystem. Typically, an existing extension has at least a clear specification such as the [FileExtension specification](https://github.com/stac-extensions/file) . An extension maturity can go as far as being integrated into a stable version of the [`pystac`][pystac-github] Python library. For instance, [FileExtension][file-extension] is available in [pystac][pystac-github] as of version 1.14.1, while `ContactExtension` (specified in the [ContactExtension specification](https://github.com/stac-extensions/contacts)) is not yet included in.

It is therefore still common to manually implement certain extensions based on their official specifications and the [pystac guidelines for adding new extensions](https://pystac.readthedocs.io/en/latest/tutorials/adding-new-and-custom-extensions.html). In such a case, we recommend adding the new extension implementation under the `STACpopulator/extensions/` directory, and then submitting a pull request (PR) to the [pystac][pystac-github] repository for its official integration. See for instance this [pull request for integrating CFExtension](https://github.com/stac-utils/pystac/pull/1592/files), where the `CFExtension` class has been implemented based on the [CFExtension specification](https://github.com/stac-extensions/cf).

In summary, it is essential to identify all relevant extensions from the available [STAC Extensions][stac-extensions] to apply in the new STAC `Populator` implementation. For example, our `RDPSpopulator` makes use of the `DataCubeExtension`, `FileExtension`, and `CFExtension` on the item/asset level, and of the `ContactExtension` on the collection level. Collection-level extensions are specifically discussed in [Section 5](#5-collection-level-extensions).

## 2. Helpers

In the `stac-populator` tool, an extension is typically applied using an associated helper. A helper extends the [`Helper`][helper-class] abstract class and implements methods for retrieving or computing the data properties to be applied by the extension. For convenience, an [`ExtensionHelper`][extension-helper-class] class extends both the [Helper][helper-class] and the pydantic [BaseModel](https://docs.pydantic.dev/latest/api/base_model/) classes to provide default constructor and validation mechanisms for defined attributes.

**A concrete helper** must extend the [Helper][helper-class] class (it is recommended to extend [ExtensionHelper][extension-helper-class] that itself inherits from [Helper][helper-class]) and implement the following:

1. Define property methods typically annotated with `@functools.cached_property`.
2. Redefine as needed the `def apply(...)` method where data properties are applied using the corresponding STAC Extension.
3. Implement a concrete `def from_data(...)` method to enable static initialization of the helper with extra kwargs.

The example below shows an excerpt of the concrete [`FileHelper`][file-helper] class. 

📝 **NOTE** - In addition to the required `data` field to compute the `file:size` property, optional keyword arguments such as the HTTP `session` can be passed in for initialization via `from_data(..., **kwargs)`. In particular, this static method facilitates instantiation of [Helper][helper-class] objects at the next layer, i.e. in the `DataModel` associated with the `Populator` implementation.

🚨 **IMPORTANT** - Variables intended to be passed via `kwargs` (e.g., `session`) should be defined using Pydantic’s [Field](https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.Field) function so they are included in the class constructor. Avoid using [PrivateAttr](https://docs.pydantic.dev/latest/api/fields/#pydantic.fields.PrivateAttr), as it excludes the variable from the constructor.

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

Inheriting from the [`BaseSTAC`](../STACpopulator/extensions/base.py#L159) class, a `DataModel` is the main data management class associated with a `Populator` implementation in `stac-populator`. It holds [Helper][helper-class] objects as attributes, which it uses to apply multiple extensions to STAC entities (i.e., [Item][pystac-item], [Asset][pystac-asset], [Link][pystac-link], or [Collection][pystac-collection]).

In `stac-populator`, the [`THREDDSCatalogDataModel`][thredds-catalog-datamodel-class] class defines the basic `DataModel` class to preprocess and integrate data properties from a THREDDS Catalog. It defines and uses two helper classes: [`THREDDSHelper`][thredds-helper], which adds general THREDDS properties from the catalog (i.e., THREDDS `services` and `links`), and [`DataCubeHelper`][datacube-helper] which adds datacube-related properties (e.g., `dimensions`, `variables`, `bounds`).

**A custom THREDDS data model class** should extend the [THREDDSCatalogDataModel][thredds-catalog-datamodel-class] aand only needs to define (as its variables) the additional concrete [Helper][helper-class] classes it will use.

📝 **NOTE** - As a best practice, helper variables should be named following the same prefix as the STAC Extension they handle. For instance, `datacube` for [DataCubeHelper][datacube-helper], `thredds` for [THREDDSHelper][thredds-helper], etc.

**Instantiation and kwargs.** `DataModel` instances should be created using their `def from_data(...)` factory method (inherited from [THREDDSCatalogDataModel][thredds-catalog-datamodel-class]). In addition to the data dictionary, this static method accepts optional keyword arguments, which are forwarded to the constructors of the concrete [Helper][helper-class] classes through their own `def from_data(...)` factory methods. The keyword arguments are dispatched to the appropriate [Helper][helper-class] classes based on their constructor signatures (e.g., variable `session` required to instantiate a [FileHelper][file-helper]), allowing the `DataModel` to accept all required parameters (typically `Populator` variables) in a single place. The instantiated [Helper][helper-class] objects are later automatically applied (using their `def apply(...)` methods) to extend the `DataModel` before the data properties are integrated.

The example below shows the [`RDPSDataModel`](../STACpopulator/extensions/rdps.py#L8). 

In addition to the default [THREDDSHelper][thredds-helper] and [DataCubeHelper][datacube-helper] inherited from `THREDDSCatalogDataModel`, this data model defines the [`CFHelper`][cf-helper] and the [`FileHelper`][file-helper], which respectively apply the `CFExtension` and `FileExtension`.

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

A `Populator` is the final stage of implementation in `stac-populator`. It consists of a class that defines methods to use the `DataModel` created in the previous stage for ingesting data from the source (e.g., a THREDDS Catalog) into the STAC API.

`Populator` classes are defined in a specific directory created under `STACpopulator/implementations/`, to which we will refer in the following as the populator's package.

📝 **NOTE** - To maintain consistency, the name of the newly created populator package should follow the naming convention: `STACpopulator/implementations/IMPLEMENTATION_AUTHOR/`. For instance, we create the `STACpopulator/implementations/RDPS_CRIM/` directory for the `RDPSpopulator`, with `RDPS_CRIM` being the package name.

### 4.1. Creating the populator class

A `Populator` class inherits from the abstract [`STACpopulatorBase`][populator-base-class] class. It must specify the corresponding `DataModel` type and implement the abstract method `def create_stac_item(...)`, which creates a data model instance for each STAC Item while applying the relevant extensions described earlier. A populator class also inherits the `def ingest(...)` method, which is called when the command associated with the populator implementation is executed, triggering the data ingestion process.

The example below shows the [`RDPSpopulator`](../STACpopulator/implementations/RDPS_CRIM/add_RDPS.py#L14) class.

```python
from typing import Any

from STACpopulator.extensions.rdps import RDPSDataModel
from STACpopulator.populator_base import STACpopulatorBase


class RDPSpopulator(STACpopulatorBase):
    """Populator that creates STAC objects representing RDPS data from a THREDDS catalog."""

    data_model = RDPSDataModel

    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Return a STAC Item."""
        # The variable `self._session` is inherited from the parent `STACpopulatorBase` class and passed as a `kwargs` to appropriate helpers via the `from_data(...)` method.
        model = self.data_model.from_data(item_data, session=self._session)
        return model.stac_item()
```

📝 **NOTE** - Optionally, populator-level variables can be passed to helpers for initialization via keyword arguments (`kwargs`) provided to the static `def from_data(...)` method of the `DataModel`. In the example above, the `self._session` variable is defined in the parent [STACpopulatorBase][populator-base-class] class. The static `def from_data(...)` method inspects the constructor signatures of the concrete [Helper][helper-class] classes to determine which variables are required to instantiate each helper and provide them. In our tutorial, the [FileHelper][file-helper] receives the `session` object for initialization and reuse it for its internal operations.  

### 4.2. Adding populator CLI command

To be able to invoke the populator from the CLI, following updates must be performed.

1. Copy the `def add_parser_args(...)` and `def runner(...)` methods from the [`STACpopulator/implementations/RDPS_CRIM/add_RDPS.py`](../STACpopulator/implementations/RDPS_CRIM/add_RDPS.py) module.
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

🚨 **IMPORTANT** - Note that programatic integration of collection-level extensions (similar to how item-level extensions are handled) is currently under active development and will be available soon.


[pystac-item]: https://pystac.readthedocs.io/en/stable/api/item.html
[pystac-collection]: https://pystac.readthedocs.io/en/stable/api/collection.html
[pystac-link]: https://pystac.readthedocs.io/en/stable/api/link.html
[pystac-asset]: https://pystac.readthedocs.io/en/stable/api/asset.html
[file-extension]: https://github.com/stac-utils/pystac/blob/main/pystac/extensions/file.py
[pystac-github]: https://github.com/stac-utils/pystac/tree/main
[stac-api]: https://github.com/radiantearth/stac-api-spec
[stac-extensions]: https://stac-extensions.github.io/
[helper-class]: ../STACpopulator/extensions/base.py#L64
[extension-helper-class]: ../STACpopulator/extensions/base.py#L78
[file-helper]: ../STACpopulator/extensions/file.py#L20
[cf-helper]: ../STACpopulator/extensions/cf.py#L46
[thredds-helper]: ../STACpopulator/extensions/thredds.py#L133
[datacube-helper]: ../STACpopulator/extensions/datacube.py#L13
[thredds-catalog-datamodel-class]: ../STACpopulator/extensions/thredds.py#L173
[populator-base-class]: ../STACpopulator/populator_base.py#L26