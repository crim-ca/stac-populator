import logging
from abc import ABC, abstractmethod
from typing import Optional

from colorlog import ColoredFormatter
from siphon.catalog import TDSCatalog

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
        pass

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

        if thredds_catalog_url.endswith(".html"):
            thredds_catalog_url = thredds_catalog_url.replace(".html", ".xml")
            LOGGER.info("Converting catalog URL from html to xml")

        self.thredds_catalog_URL = thredds_catalog_url
        self.catalog = TDSCatalog(self.thredds_catalog_URL)
        self.catalog_head = self.catalog

    def reset(self):
        """Reset the generator."""
        self.catalog_head = self.catalog

    def __iter__(self):
        """Return a generator walking a THREDDS data catalog for datasets."""
        yield from self.catalog_head.datasets.items()

        if self._depth > 0:
            for name, ref in self.catalog_head.catalog_refs.items():
                self.catalog_head = ref.follow()
                self._depth -= 1
                yield from self


class RemoteTHREDDSLoader(THREDDSLoader):
    def __init__(self, thredds_catalog_url: str, depth: int | None = None) -> None:
        super().__init__(thredds_catalog_url, depth)
        # more stuff to follow based on needs of a concrete implementation


class GeoServerLoader(GenericLoader):
    def __init__(self) -> None:
        super().__init__()

    def __iter__(self):
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError
