import json
import logging
import os
import pathlib
import queue
import re
from abc import ABC, abstractmethod
from typing import Any, Iterator, Literal, MutableMapping, Optional, Tuple
from urllib.parse import urlparse
from xml.etree import ElementTree

import pystac
import requests
import xncml
from requests.sessions import Session
from siphon.catalog import Dataset, TDSCatalog, session_manager

from STACpopulator.stac_utils import ServiceType, numpy_to_python_datatypes

LOGGER = logging.getLogger(__name__)


class GenericLoader(ABC):
    """Generic data loader class."""

    def __init__(self) -> None:
        self.links = []

    @abstractmethod
    def __iter__(self) -> Iterator[Tuple[str, str, MutableMapping[str, Any]]]:
        """
        Iterate over this loader.

        Returns items from the input. Items return a tuple containing the object name,
        path to the object, and the object data.
        """
        raise NotImplementedError


class ErrorLoader(GenericLoader):
    """A data loader that will raise an error if used."""

    def __init__(self) -> None:
        raise NotImplementedError

    def __iter__(self) -> Iterator:
        """Iterate over this loader."""
        raise NotImplementedError


class THREDDSLoader(GenericLoader):
    """Data loader from a THREDDS instance."""

    def __init__(
        self,
        thredds_catalog_url: str,
        depth: Optional[int] = None,
        session: Optional[Session] = None,
    ) -> None:
        """Initialize the THREDDS loader.

        :param thredds_catalog_url: the URL to the THREDDS catalog to ingest
        :type thredds_catalog_url: str
        :param depth: Maximum recursive depth for the class's generator. Setting 0 will return only datasets within the
          top-level catalog. If None, depth is unlimited.
        :type depth: int, optional
        """
        super().__init__()
        self.depth = depth
        self.session = session or requests.Session()
        session_manager.set_session_options(**vars(self.session))
        if urlparse(thredds_catalog_url).query:
            raise RuntimeError("THREDDS catalog URL should not contain any query parameters")
        try:
            self.catalog = TDSCatalog(thredds_catalog_url)
        except requests.exceptions.RequestException as exc:
            LOGGER.error(
                "Could not access THREDDS host. Not reachable [%s] due to [%s]", thredds_catalog_url, exc, exc_info=exc
            )
        self.links.append(
            pystac.Link(
                rel="source", target=self.catalog.catalog_url, media_type="application/xml", title="THREDDS data source"
            )
        )

    def __iter__(self) -> Iterator[Tuple[str, str, MutableMapping[str, Any]]]:
        """Return a generator walking a THREDDS data catalog for datasets.

        :yield: Returns three quantities: name of the item, location of the item, and its attributes
        :rtype: Iterator[Tuple[str, str, MutableMapping[str, Any]]]
        """
        catalogs = queue.SimpleQueue()
        catalogs.put(self.catalog)

        while not catalogs.empty():
            current_catalog: Dataset = catalogs.get()
            for item_name, dataset in current_catalog.datasets.items():
                self._update_access_urls(current_catalog, dataset)
                self._add_WxS_queries(dataset)
                attrs = self.extract_metadata(dataset)
                filename = dataset.url_path.split("/")[-1]
                url = current_catalog.catalog_url[: current_catalog.catalog_url.rfind("/")] + filename
                url = f"{current_catalog.catalog_url}?dataset={dataset.id}"
                yield item_name, url, attrs

            for ref in current_catalog.catalog_refs:
                catalogs.put(ref.follow())

    def __getitem__(self, dataset: str) -> dict:
        """Return the given dataset."""
        return self.catalog.datasets[dataset]

    def _update_access_urls(self, catalog: TDSCatalog, dataset: Dataset) -> None:
        """
        Update access_urls for the given dataset to include missing urls.

        This method is only required until https://github.com/Unidata/siphon/issues/932
        is resolved. After it is resolved additional updates may be needed depending on
        how the fix is implemented.
        """
        dataset_xml_path = f"{catalog.catalog_url}?dataset={dataset.url_path}"
        resp = self.session.get(dataset_xml_path)
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            LOGGER.warning(
                "Could not update access_urls for dataset [%s] due to [%s]", dataset.url_path, resp.text, exc_info=exc
            )
        root = ElementTree.fromstring(resp.content)
        dataset.access_urls.clear()
        for service in root.iterfind(".//{*}service[@serviceType!='Compound']"):
            url = catalog.base_tds_url + service.attrib["base"] + dataset.url_path
            key = service.attrib["serviceType"]
            if key == "NetcdfSubset":
                base_components = service.attrib["base"].split("/")
                if "point" in base_components:
                    key = ServiceType.netcdfsubsetpoint
                elif "grid" in base_components:
                    key = ServiceType.netcdfsubsetgrid
            dataset.access_urls[key] = url

    def _add_WxS_queries(self, dataset: Dataset) -> None:
        """Update access_urls for WxS services to include the GetCapabilities request parameter."""
        for key, val in dataset.access_urls.items():
            if re.match(r"W[CM]S", key):
                dataset.access_urls[key] = f"{val}?request=GetCapabilities"

    def extract_metadata(self, dataset: Dataset) -> MutableMapping[str, Any]:
        """Extract metadata from an NcML item."""
        attrs = {}
        if "NCML" in dataset.access_urls:
            LOGGER.info("Requesting NcML dataset description")
            url = dataset.access_urls["NCML"]
            try:
                r = self.session.get(url)
                r.raise_for_status()
            except requests.exceptions.RequestException as exc:
                LOGGER.error("Could not access THREDDS dataset. Not reachable [%s] due to [%s]", url, exc, exc_info=exc)
            # Convert NcML to CF-compliant dictionary
            attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
            attrs["attributes"] = numpy_to_python_datatypes(attrs["attributes"])
        # access URLs should ideally be added with xncml but they're not so add them in from the siphon catalog for now.
        attrs["access_urls"] = dataset.access_urls
        return attrs


class STACDirectoryLoader(GenericLoader):
    """
    Iterates through a directory structure looking for STAC Collections or Items.

    For each directory that gets crawled, all files that match the glob pattern that provided by the include parameter
    will be read.

    If the mode parameter is ``"collection"`` only STAC collection files will be processed.
    If the mode parameter is ``"item"`` only STAC item files will be processed.

    Using the mode option, yielded results will be either the STAC Collections or the STAC Items.
    This allows this class to be used in conjunction (2 nested loops) to find collections and their underlying items.

    .. code-block:: python

        for collection_path, collection_json in STACDirectoryLoader(
            dir_path, mode="collection", include="collection*.json"
        ):
            for item_path, item_json in STACDirectoryLoader(
                os.path.dirname(collection_path), mode="item", include="item*.json", prune=True
            ):
                ...  # do stuff

    The prune parameter can be used to ignore STAC items that appear in subdirectories once an initial collection
    is found.
    If prune is ``True`` subdirectories will not be traversed once a collection is found.
    For example, if prune is ``True``, the ``collection2/`` and ``collection3-subdir/`` directories will be ignored
    because they are nested under a directory that already contains a collection file.

    catalog/
    ├── collection1/
    │   ├── collection.json
    │   ├── item1.json
    │   └── collection2/
    │       ├── collection.json
    │       └── item2.json
    └── collection3/
        ├── collection.json
        ├── item3.json
        └── collection3-subdir/
            └── item3.json
    """

    def __init__(
        self,
        path: str,
        mode: Literal["collection", "item"],
        item_pattern: str = r"item.*\.(geo)?json$",
        collection_pattern: str = r"collection\.json$",
        prune: bool = False,
    ) -> None:
        super().__init__()
        self.path = pathlib.Path(path)
        self.mode = mode
        self.prune = prune
        self.item_pattern = item_pattern
        self.collection_pattern = collection_pattern

    def _load_stac_file(self, path: os.PathLike) -> dict:
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            LOGGER.error("Could not load STAC object from file [%s] due to [%s]", path, exc, exc_info=exc)

    def _check_stac_file(self, path: pathlib.Path, pattern: str, stac_type: str) -> dict | None:
        if re.match(pattern, path.name):
            stac_data = self._load_stac_file(path)
            if stac_data["type"] == stac_type:
                return stac_data

    def __iter__(self) -> Iterator[Tuple[str, str, MutableMapping[str, Any]]]:
        """Return a generator that walks through a directory structure looking for STAC Collections or Items.

        :yield: Returns three quantities: name of the item, location of the item, and its attributes
        :rtype: Iterator[Tuple[str, str, MutableMapping[str, Any]]]
        """
        collection_dirs = set()
        for dirpath, dirnames, filenames in os.walk(self.path):
            dirpath = pathlib.Path(dirpath)  # pathlib.Path.walk is not supported for python < 3.12
            skip_items = False
            for f in filenames:
                filepath = dirpath / f
                data = self._check_stac_file(filepath, self.collection_pattern, "Collection")
                if data is None:
                    # not a real collection
                    continue
                if dirpath in collection_dirs:
                    # collection already found in this directory
                    LOGGER.warning(
                        "Path '%s' contains multiple collection files. File '%s' will be skipped", dirpath, f
                    )
                    continue
                if self.mode == "collection":
                    path_str = str(filepath)
                    yield path_str, path_str, data
                elif set(dirpath.parents) & collection_dirs:
                    # items in this directory belong to a different collection, skip them
                    dirnames.clear()
                    skip_items = True
                    break
                if self.prune:
                    dirnames.clear()
                collection_dirs.add(dirpath)
            if self.mode == "item" and not skip_items:
                for f in filenames:
                    filepath = dirpath / f
                    data = self._check_stac_file(filepath, self.item_pattern, "Feature")
                    if data is not None:
                        path_str = str(filepath)
                        yield path_str, path_str, data


class STACLoader(GenericLoader):
    """Data loader from a STAC catalog instance."""

    def __init__(self) -> None:
        super().__init__()

    def __iter__(self) -> Iterator:
        """Iterate over this loader."""
        raise NotImplementedError


class GeoServerLoader(GenericLoader):
    """Data loader from a Geoserver instance."""

    def __init__(self) -> None:
        super().__init__()

    def __iter__(self) -> Iterator:
        """Iterate over this loader."""
        raise NotImplementedError
