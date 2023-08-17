import hashlib
import logging
from abc import ABC, abstractmethod

import yaml
from colorlog import ColoredFormatter

from STACpopulator.input import GenericLoader
from STACpopulator.stac_utils import (
    create_stac_collection,
    post_collection,
    stac_collection_exists,
    stac_host_reachable,
    url_validate,
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
        stac_host: str,
        data_loader: GenericLoader,
        collection_info_filename: str,
    ) -> None:
        """Constructor

        :param stac_host: URL to the STAC API
        :type stac_host: str
        :param data_loader: A concrete implementation of the GenericLoader abstract base class
        :type data_loader: GenericLoader
        :param collection_info_filename: Yaml file containing the information about the collection to populate
        :type collection_info_filename: str
        :raises RuntimeError: Raised if one of the required definitions is not found in the collection info filename
        """

        super().__init__()
        with open(collection_info_filename) as f:
            self._collection_info = yaml.load(f, yaml.Loader)

        req_definitions = ["title", "description", "keywords", "license"]
        for req in req_definitions:
            if req not in self._collection_info.keys():
                LOGGER.error(f"'{req}' is required in the configuration file")
                raise RuntimeError(f"'{req}' is required in the configuration file")

        self._ingest_pipeline = data_loader
        self._stac_host = self.validate_host(stac_host)

        self._collection_id = hashlib.md5(self.collection_name.encode("utf-8")).hexdigest()
        LOGGER.info("Initialization complete")
        LOGGER.info(f"Collection {self.collection_name} is assigned id {self._collection_id}")

    @property
    def collection_name(self) -> str:
        return self._collection_info["title"]

    @property
    def stac_host(self) -> str:
        return self._stac_host

    @property
    def collection_id(self) -> str:
        return self._collection_id

    def validate_host(self, stac_host: str) -> str:
        if not url_validate(stac_host):
            raise ValueError("stac_host URL is not appropriately formatted")
        if not stac_host_reachable(stac_host):
            raise ValueError("stac_host is not reachable")

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
    def process_stac_item(self):  # noqa N802
        pass

    @abstractmethod
    def validate_stac_item_cv(self):  # noqa N802
        pass
