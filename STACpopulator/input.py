import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Iterator, Literal, MutableMapping, Optional, Tuple, Union

import pystac
import requests
import siphon
import xncml
from colorlog import ColoredFormatter
from siphon.catalog import TDSCatalog

from STACpopulator.stac_utils import numpy_to_python_datatypes, url_validate

LOGGER = logging.getLogger(__name__)
LOGFORMAT = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s"
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setFormatter(formatter)
LOGGER.addHandler(stream)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


class GenericLoader(ABC):
    def __init__(self) -> None:
        self.links = []

    @abstractmethod
    def __iter__(self):
        """
        A generator that returns an item from the input. The item could be anything
        depending on the specific concrete implementation of this abstract class.
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        """Reset the internal state of the generator."""
        raise NotImplementedError


class ErrorLoader(GenericLoader):
    def __init__(self):  # noqa
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


class THREDDSLoader(GenericLoader):
    def __init__(self, thredds_catalog_url: str, depth: Optional[int] = None) -> None:
        """Constructor

        :param thredds_catalog_url: the URL to the THREDDS catalog to ingest
        :type thredds_catalog_url: str
        :param depth: Maximum recursive depth for the class's generator. Setting 0 will return only datasets within the
          top-level catalog. If None, depth is set to 1000, defaults to None
        :type depth: int, optional
        """
        super().__init__()
        self._depth = depth if depth is not None else 1000

        self.thredds_catalog_URL = self.validate_catalog_url(thredds_catalog_url)

        self.catalog = TDSCatalog(self.thredds_catalog_URL)
        self.catalog_head = self.catalog
        self.links.append(self.magpie_collection_link())

    def validate_catalog_url(self, url: str) -> str:
        """Validate the user-provided catalog URL.

        :param url: URL to the THREDDS catalog
        :type url: str
        :raises RuntimeError: if URL is invalid or contains query parameters.
        :return: a valid URL
        :rtype: str
        """
        if url_validate(url):
            if "?" in url:
                raise RuntimeError("THREDDS catalog URL should not contain query parameter")
        else:
            raise RuntimeError("Invalid URL")

        return url.replace(".html", ".xml") if url.endswith(".html") else url

    def magpie_collection_link(self) -> pystac.Link:
        """Creates a PySTAC Link for the collection that is used by Cowbird and Magpie.

        :return: A PySTAC Link
        :rtype: pystac.Link
        """
        url = self.thredds_catalog_URL
        parts = url.split("/")
        i = parts.index("catalog")
        service = parts[i - 1]
        path = "/".join(parts[i + 1 : -1])
        title = f"{service}:{path}"
        return pystac.Link(rel="source", target=url, media_type="text/xml", title=title)

    def reset(self):
        """Reset the generator."""
        self.catalog_head = self.catalog

    def __iter__(self) -> Iterator[Tuple[str, MutableMapping[str, Any]]]:
        """Return a generator walking a THREDDS data catalog for datasets."""
        if self.catalog_head.datasets.items():
            for item_name, ds in self.catalog_head.datasets.items():
                attrs = self.extract_metadata(ds)
                yield item_name, attrs

        if self._depth > 0:
            for name, ref in self.catalog_head.catalog_refs.items():
                self.catalog_head = ref.follow()
                self._depth -= 1
                yield from self

    def __getitem__(self, dataset):
        return self.catalog.datasets[dataset]

    def extract_metadata(self, ds: siphon.catalog.Dataset) -> MutableMapping[str, Any]:
        LOGGER.info("Requesting NcML dataset description")
        url = ds.access_urls["NCML"]
        r = requests.get(url)
        # Convert NcML to CF-compliant dictionary
        attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
        attrs["attributes"] = numpy_to_python_datatypes(attrs["attributes"])
        attrs["access_urls"] = ds.access_urls
        return attrs


class STACDirectoryLoader(GenericLoader):
    """
    Iterates through a directory structure looking for STAC Collections or Items.

    For each directory that gets crawled, if a file is named ``collection.json``, it assumed to be a STAC Collection.
    All other ``.json`` files under the directory where ``collection.json`` was found are assumed to be STAC Items.
    These JSON STAC Items can be either at the same directory level as the STAC Collection, or under nested directories.

    Using the mode option, yielded results will be either the STAC Collections or the STAC Items.
    This allows this class to be used in conjunction (2 nested loops) to find collections and their underlying items.

    .. code-block:: python

        for collection_path, collection_json in STACDirectoryLoader(dir_path, mode="collection"):
            for item_path, item_json in STACDirectoryLoader(collection_path, mode="item"):
                ...  # do stuff

    For convenience, option ``prune`` can be used to stop crawling deeper once a STAC Collection is found.
    Any collection files found further down the directory were a top-most match was found will not be yielded.
    This can be useful to limit search, or to ignore nested directories using subsets of STAC Collections.
    """

    def __init__(self, path: str, mode: Literal["collection", "item"], prune: bool = False) -> None:
        super().__init__()
        self.path = path
        self.iter = None
        self.prune = prune
        self.reset()
        self._collection_mode = mode == "collection"
        self._collection_name = "collection.json"

    def __iter__(self) -> Iterator[Tuple[str, MutableMapping[str, Any]]]:
        for root, dirs, files in self.iter:
            if self.prune and self._collection_mode and self._collection_name in files:
                del dirs[:]
            for name in files:
                if self._collection_mode and self._is_collection(name):
                    col_path = os.path.join(root, name)
                    yield col_path, self._load_json(col_path)
                elif not self._collection_mode and self._is_item(name):
                    item_path = os.path.join(root, name)
                    yield item_path, self._load_json(item_path)

    def _is_collection(self, path: Union[os.PathLike[str], str]) -> bool:
        name = os.path.split(path)[-1]
        return name == self._collection_name

    def _is_item(self, path: Union[os.PathLike[str], str]) -> bool:
        name = os.path.split(path)[-1]
        return name != self._collection_name and os.path.splitext(name)[-1] in [".json", ".geojson"]

    def _load_json(self, path: Union[os.PathLike[str], str]) -> MutableMapping[str, Any]:
        with open(path, mode="r", encoding="utf-8") as file:
            return json.load(file)

    def reset(self):
        self.iter = os.walk(self.path)


class STACLoader(GenericLoader):
    def __init__(self) -> None:
        super().__init__()

    def __iter__(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError


class GeoServerLoader(GenericLoader):
    def __init__(self) -> None:
        super().__init__()

    def __iter__(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError
