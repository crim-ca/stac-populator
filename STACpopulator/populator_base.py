import functools
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Type

import pystac
from colorlog import ColoredFormatter
from requests.sessions import Session

from STACpopulator.api_requests import (
    post_stac_collection,
    post_stac_item,
    stac_host_reachable,
)
from STACpopulator.input import GenericLoader
from STACpopulator.models import AnyGeometry
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
        session: Optional[Session] = None,
    ) -> None:
        """Constructor

        :param stac_host: URL to the STAC API
        :type stac_host: str
        :param data_loader: A concrete implementation of the GenericLoader abstract base class
        :type data_loader: GenericLoader
        :raises RuntimeError: Raised if one of the required definitions is not found in the collection info filename
        """

        super().__init__()
        self._collection_info = None
        self._session = session
        self.load_config()

        self._ingest_pipeline = data_loader
        self._stac_host = self.validate_host(stac_host)
        self.update = update

        LOGGER.info("Initialization complete")
        LOGGER.info(f"Collection {self.collection_name} is assigned ID {self.collection_id}")
        self.create_stac_collection()

    def load_config(self):
        self._collection_info = load_collection_configuration()

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
    def item_geometry_model(self) -> Type[AnyGeometry]:
        """
        Implementation of the expected Geometry representation in derived classes.
        """
        raise NotImplementedError

    @abstractmethod
    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def validate_host(self, stac_host: str) -> str:
        if not url_validate(stac_host):
            raise ValueError("stac_host URL is not appropriately formatted")
        if not stac_host_reachable(stac_host, session=self._session):
            raise RuntimeError("stac_host is not reachable")

        return stac_host

    # FIXME: should provide a way to update after item generation
    #   STAC collections are supposed to include 'summaries' with
    #   an aggregation of all supported 'properties' by its child items
    @functools.cache
    def create_stac_collection(self) -> dict[str, Any]:
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
        collection_data = collection.to_dict()
        self.publish_stac_collection(collection_data)
        return collection_data

    def publish_stac_collection(self, collection_data: dict[str, Any]) -> None:
        post_stac_collection(self.stac_host, collection_data, self.update, session=self._session)

    def ingest(self) -> None:
        LOGGER.info("Data ingestion")
        for item_name, item_data in self._ingest_pipeline:
            LOGGER.info(f"Creating STAC representation for {item_name}")
            stac_item = self.create_stac_item(item_name, item_data)
            if stac_item:
                post_stac_item(
                    self.stac_host,
                    self.collection_id,
                    item_name,
                    stac_item,
                    update=self.update,
                    session=self._session,
                )
