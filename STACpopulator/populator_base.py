import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Iterator, Optional

import yaml
from colorlog import ColoredFormatter
from siphon.catalog import TDSCatalog

from STACpopulator.crawlers import Crawler
from STACpopulator.stac_utils import (
    create_stac_collection,
    post_collection,
    stac_collection_exists,
)

LOGGER = logging.getLogger(__name__)
LOGFORMAT = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s"
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setFormatter(formatter)
LOGGER.addHandler(stream)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


class STACpopulatorBase(ABC):
    def __init__(
        self,
        catalog: str,
        stac_host: str,
        collection_info_filename: str,
        crawler: Crawler,
        crawler_args: Optional[dict] = {},
    ) -> None:
        """Constructor

        Parameters
        ----------
        catalog : str
        stac_host : STAC API address
        collection_info_filename : Name of the configuration file containing info about the collection
        crawler : callable that knows how to iterate over the organization
                  structure of the catalog in order to find individual items
        crawler_args : any optional arguments to pass to the crawler
        """

        super().__init__()
        with open(collection_info_filename) as f:
            self._collection_info = yaml.load(f, yaml.Loader)

        req_definitions = ["title", "description", "keywords", "license"]
        for req in req_definitions:
            if req not in self._collection_info.keys():
                LOGGER.error(f"'{req}' is required in the configuration file")
                raise RuntimeError(f"'{req}' is required in the configuration file")

        if catalog.endswith(".html"):
            catalog = catalog.replace(".html", ".xml")
            LOGGER.info("Converting catalog URL from html to xml")
        self._catalog = TDSCatalog(catalog)
        self._stac_host = self.validate_host(stac_host)
        self._crawler = crawler
        self._crawler_args = crawler_args

        self._collection_id = hashlib.md5(self.collection_name.encode("utf-8")).hexdigest()
        LOGGER.info("Initialization complete")
        LOGGER.info(f"Collection {self.collection_name} is assigned id {self._collection_id}")

    @property
    def catalog(self) -> TDSCatalog:
        return self._catalog

    @property
    def collection_name(self) -> str:
        return self._collection_info["title"]

    @property
    def stac_host(self) -> str:
        return self._stac_host

    @property
    def crawler(self) -> Crawler:
        return self._crawler

    @property
    def collection_id(self) -> str:
        return self._collection_id

    def validate_host(self, stac_host: str) -> str:
        # TODO: check the format of the host is URL type
        # TODO: check if the host is reachable??
        return stac_host

    def ingest(self) -> None:
        # First create collection if it doesn't exist
        if not stac_collection_exists(self.stac_host, self.collection_id):
            LOGGER.info(f"Creating collection '{self.collection_name}'")
            pystac_collection = create_stac_collection(self.collection_id, self._collection_info)
            post_collection(self.stac_host, pystac_collection)
            LOGGER.info("Collection successfully created")
        else:
            LOGGER.info(f"Collection '{self.collection_name}' already exists")
        # for item in self.crawler(self.catalog, **self._crawler_args):
        #     stac_item = self.process_STAC_item(item)
        #     self.post_item(stac_item)

    def post_item(self, data: dict[str, dict]) -> None:
        pass

    @abstractmethod
    def process_STAC_item(self):  # noqa N802
        pass

    @abstractmethod
    def validate_STAC_item_CV(self):  # noqa N802
        pass
