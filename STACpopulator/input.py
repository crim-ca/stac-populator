import logging
from abc import ABC, abstractmethod
from typing import Any, Iterator, MutableMapping, Optional, Tuple

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
        pass

    @abstractmethod
    def reset(self):
        """Reset the internal state of the generator."""
        pass


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
        # service = parts[i - 1]
        path = "/".join(parts[i + 1 : -1])
        return pystac.Link(rel="source", target=url, media_type="text/xml", title=path)

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
        attrs = xncml.Dataset.from_text(r.content).to_cf_dict()
        attrs["attributes"] = numpy_to_python_datatypes(attrs["attributes"])
        attrs["access_urls"] = ds.access_urls
        return attrs


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
