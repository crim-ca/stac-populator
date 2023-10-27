import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, MutableMapping, Optional

import pystac
from colorlog import ColoredFormatter

from STACpopulator.api_requests import (
    post_stac_collection,
    post_stac_item,
    stac_host_reachable,
)
from STACpopulator.input import GenericLoader
from STACpopulator.stac_utils import load_collection_configuration, url_validate

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
        update: Optional[bool] = False,
    ) -> None:
        """Constructor

        :param stac_host: URL to the STAC API
        :type stac_host: str
        :param data_loader: A concrete implementation of the GenericLoader abstract base class
        :type data_loader: GenericLoader
        :raises RuntimeError: Raised if one of the required definitions is not found in the collection info filename
        """

        super().__init__()
        self._collection_info = load_collection_configuration()

        self._ingest_pipeline = data_loader
        self._stac_host = self.validate_host(stac_host)
        self.update = update

        self._collection_id = self.collection_name
        LOGGER.info("Initialization complete")
        LOGGER.info(f"Collection {self.collection_name} is assigned id {self._collection_id}")
        self.create_stac_collection()

    @property
    def collection_name(self) -> str:
        return self._collection_info["title"]

    @property
    def stac_host(self) -> str:
        return self._stac_host

    @property
    def collection_id(self) -> str:
        return self._collection_info["id"]

    @property
    @abstractmethod
    def item_properties_model(self):
        """In derived classes, this property should be defined as a pydantic data model that derives from
        models.STACItemProperties."""
        raise NotImplementedError

    @property
    @abstractmethod
    def item_geometry_model(self):
        """In derived classes, this property should be defined as a pydantic data model that derives from
        models.STACItemProperties."""
        raise NotImplementedError

    @abstractmethod
    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        raise NotImplementedError

    def validate_host(self, stac_host: str) -> str:
        if not url_validate(stac_host):
            raise ValueError("stac_host URL is not appropriately formatted")
        if not stac_host_reachable(stac_host):
            raise RuntimeError("stac_host is not reachable")

        return stac_host

    def create_stac_collection(self) -> None:
        """
        Create a basic STAC collection.

        Returns the collection.
        """
        LOGGER.info(f"Creating collection '{self.collection_name}'")
        sp_extent = pystac.SpatialExtent([self._collection_info.pop("spatialextent")])
        tmp = self._collection_info.pop("temporalextent")
        tmp_extent = pystac.TemporalExtent(
            [
                [
                    datetime.strptime(tmp[0], "%Y-%m-%d") if tmp[0] is not None else None,
                    datetime.strptime(tmp[1], "%Y-%m-%d") if tmp[1] is not None else None,
                ]
            ]
        )
        self._collection_info["extent"] = pystac.Extent(sp_extent, tmp_extent)
        self._collection_info["summaries"] = pystac.Summaries({"needs_summaries_update": ["true"]})
        collection = pystac.Collection(**self._collection_info)

        collection.add_links(self._ingest_pipeline.links)

        post_stac_collection(self.stac_host, collection.to_dict(), self.update)

    def ingest(self) -> None:
        LOGGER.info("Data ingestion")
        for item_name, item_data in self._ingest_pipeline:
            LOGGER.info(f"Creating STAC representation for {item_name}")
            stac_item = self.create_stac_item(item_name, item_data)
            post_stac_item(self.stac_host, self.collection_id, item_name, stac_item, self.update)
