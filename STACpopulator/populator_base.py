import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any, MutableMapping

import yaml
from colorlog import ColoredFormatter

from STACpopulator.input import GenericLoader
from STACpopulator.stac_utils import (
    create_stac_collection,
    post_stac_collection,
    post_stac_item,
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
        self.create_collection()

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

    def create_collection(self):
        if not stac_collection_exists(self.stac_host, self.collection_id):
            LOGGER.info(f"Creating collection '{self.collection_name}'")
            pystac_collection = create_stac_collection(self.collection_id, self._collection_info)
            post_stac_collection(self.stac_host, pystac_collection)
            LOGGER.info("Collection successfully created")
        else:
            LOGGER.info(f"Collection '{self.collection_name}' already exists")

    def ingest(self) -> None:
        for item_name, item_data in self._ingest_pipeline:
            LOGGER.info(f"Creating STAC representation for {item_name}")
            stac_item = self.create_stac_item(item_name, item_data)
            if self.validate_stac_item_cv(stac_item):
                if post_stac_item(self.stac_host, self.collection_id, stac_item):
                    LOGGER.info(f"{item_name} successfully posted")
                else:
                    LOGGER.error(f"Posting {item_name} failed")
                    self.handle_ingestion_error("Posting Error", item_name, item_data)
            else:
                LOGGER.error(f"Validation failed for item {item_name}")
                self.handle_ingestion_error("Validation Error", item_name, item_data)

    @abstractmethod
    def handle_ingestion_error(self, error: str, item_name: str, item_data: MutableMapping[str, Any]):
        pass

    @abstractmethod
    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        pass

    @abstractmethod
    def validate_stac_item_cv(self, data: MutableMapping[str, Any]) -> bool:
        pass
