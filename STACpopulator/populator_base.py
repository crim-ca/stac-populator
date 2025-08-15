import functools
import inspect
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Iterable, List, Literal, MutableMapping, Optional, Type, Union

import pystac
from requests.sessions import Session

from STACpopulator.api_requests import (
    post_stac_collection,
    post_stac_item,
    stac_host_reachable,
    stac_version_match,
)
from STACpopulator.input import GenericLoader
from STACpopulator.models import AnyGeometry
from STACpopulator.stac_utils import load_config

LOGGER = logging.getLogger(__name__)


class STACpopulatorBase(ABC):
    """Abstract base class for STAC populators."""

    def __init__(
        self,
        stac_host: str,
        data_loader: GenericLoader,
        update: bool = False,
        session: Optional[Session] = None,
        config_file: Optional[Union[os.PathLike[str], str]] = "collection_config.yml",
        update_collection: Literal["extents", "summaries", "all", "none"] = "none",
        exclude_summaries: Iterable[str] = (),
    ) -> None:
        """Initialize the STAC populator.

        :param stac_host: URL to the STAC API
        :type stac_host: str
        :param data_loader: A concrete implementation of the GenericLoader abstract base class
        :type data_loader: GenericLoader
        :raises RuntimeError: Raised if one of the required definitions is not found in the collection info filename
        """
        self._collection_config_path = config_file
        self._collection_info: MutableMapping[str, Any] = None
        self._session = session
        self.load_config()

        self._ingest_pipeline = data_loader
        self._stac_host = self.validate_host(stac_host)
        self.update = update
        self.update_collection = update_collection

        # the STAC spec does not recommend repeating summaries that are covered by the extent already
        self.exclude_summaries = ["datetime", "start_datetime", "end_datetime"]
        self.exclude_summaries.extend(exclude_summaries)

        LOGGER.info("Initialization complete")
        LOGGER.info(f"Collection {self.collection_name} is assigned ID {self.collection_id}")
        self._collection = self.create_stac_collection()

    def load_config(self) -> None:
        """
        Read details of the STAC Collection to be created from a configuration file.

        Once called, the collection information attribute should be set with relevant mapping attributes.
        """
        # use explicit override, or default to local definition
        if not self._collection_config_path or not os.path.isfile(self._collection_config_path):
            impl_path = inspect.getfile(self.__class__)
            impl_dir = os.path.dirname(impl_path)
            impl_cfg = os.path.join(impl_dir, "collection_config.yml")
            self._collection_config_path = impl_cfg

        LOGGER.info("Using populator collection configuration file: [%s]", self._collection_config_path)
        collection_info = load_config(self._collection_config_path)

        req_definitions = ["title", "id", "description", "keywords", "license"]
        for req in req_definitions:
            if req not in collection_info.keys():
                mgs = f"'{req}' is required in the configuration file [{self._collection_config_path}]"
                LOGGER.error(mgs)
                raise RuntimeError(mgs)

        self._collection_info = collection_info

    @property
    def collection_name(self) -> str:
        """Return the populator's collection name."""
        return self._collection_info["title"]

    @property
    def stac_host(self) -> str:
        """Return the STAC host URL that will be used to upload new data to."""
        return self._stac_host

    @property
    def collection_id(self) -> str:
        """Return the populator's collection id."""
        return self._collection_info["id"]

    @property
    @abstractmethod
    def item_geometry_model(self) -> Type[AnyGeometry]:
        """Return a geometry model class that represents the geometry used in this populator."""
        raise NotImplementedError

    @abstractmethod
    def create_stac_item(self, item_name: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """Create a STAC item."""
        raise NotImplementedError

    def validate_host(self, stac_host: str) -> str:
        """Validate that the given STAC host can be used to upload data to."""
        if not stac_host_reachable(stac_host, session=self._session):
            raise RuntimeError("stac_host is not reachable")
        if not stac_version_match(stac_host, session=self._session):
            raise RuntimeError("stac_version of the stac_host does not match the version used by pystac.")

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

        # Add any assets if provided in the config
        self._collection_info["assets"] = self.__make_collection_assets()

        # Construct links if provided in the config. This needs to be done before constructing a collection object.
        collection_links = self.__make_collection_links()

        collection = pystac.Collection(**self._collection_info)

        if collection_links:
            collection.add_links(collection_links)
        collection.add_links(self._ingest_pipeline.links)
        collection_data = collection.to_dict()
        self.publish_stac_collection(collection_data)
        return collection_data

    def __make_collection_links(self) -> List[pystac.Link]:
        """Create collection level links based on data read in from the configuration file.

        :return: List of pystac Link objects
        :rtype: List[pystac.Link]
        """
        links = []
        config_links = self._collection_info.pop("links", {})
        for link_info in config_links:
            links.append(pystac.Link(**link_info))
        return links

    def __make_collection_assets(self) -> Dict[str, pystac.Asset]:
        """Create collection level assets based on data read in from the configuration file.

        :return: Dictionary of pystac Asset objects
        :rtype: Dict[pystac.Asset]
        """
        pystac_assets = {}
        if "assets" in self._collection_info:
            for asset_name, asset_info in self._collection_info["assets"].items():
                pystac_assets[asset_name] = pystac.Asset(**asset_info)
        return pystac_assets

    def publish_stac_collection(self, collection_data: dict[str, Any]) -> None:
        """Publish this collection by uploading it to the STAC catalog at self.stac_host."""
        post_stac_collection(self.stac_host, collection_data, self.update, session=self._session)

    @staticmethod
    def _check_wgs84_compliance(bbox: list[int | float], stac_object_type: str, stac_object_id: str | None) -> None:
        longitude = (bbox[0], bbox[len(bbox) // 2])
        latitude = (bbox[1], bbox[(len(bbox) // 2) + 1])
        for lon in longitude:
            if lon < -180 or lon > 180:
                LOGGER.warning(
                    "STAC %s with id [%s] contains a bbox with a longitude outside of the accepted range of -180 and 180",
                    stac_object_type,
                    stac_object_id,
                )
        for lat in latitude:
            if lat < -90 or lat > 90:
                LOGGER.warning(
                    "STAC %s with id [%s] contains a bbox with a latitude outside of the accepted range of -90 and 90",
                    stac_object_type,
                    stac_object_id,
                )

    @staticmethod
    def _sorted_bbox(bbox: list[int | float]) -> list[int | float]:
        return [
            a for b in zip(*(sorted(axis) for axis in zip(bbox[: len(bbox) // 2], bbox[len(bbox) // 2 :]))) for a in b
        ]

    def _update_collection_bbox(self, stac_item: dict[str, Any]) -> None:
        item_bbox = stac_item.get("bbox")
        if item_bbox is None:
            # bbox can be missing if there is no geometry
            return
        sorted_bbox = self._sorted_bbox(item_bbox)
        if item_bbox != sorted_bbox:
            LOGGER.warning(
                "STAC item with id [%s] contains a bbox with unsorted values: %s should be %s",
                stac_item.get("id"),
                item_bbox,
                sorted_bbox,
            )
            item_bbox = sorted_bbox
        self._check_wgs84_compliance(item_bbox, "item", stac_item.get("id"))
        collection_bboxes = self._collection["extent"]["spatial"]["bbox"]
        if collection_bboxes:
            collection_bbox = collection_bboxes[0]
            if len(item_bbox) == 4 and len(collection_bbox) == 6:
                # collection bbox has a z axis and item bbox does not
                item_bbox = [*item_bbox[:2], collection_bbox[2], item_bbox[2:], collection_bbox[5]]
            elif len(item_bbox) == 6 and len(collection_bbox) == 4:
                # item bbox has a z axis and collection bbox does not
                collection_bbox.insert(2, item_bbox[2])
                collection_bbox.append(item_bbox[5])
            for i in range(len(item_bbox) // 2):
                if item_bbox[i] < collection_bbox[i]:
                    collection_bbox[i] = item_bbox[i]
            for i in range(len(item_bbox) // 2, len(item_bbox)):
                if item_bbox[i] > collection_bbox[i]:
                    collection_bbox[i] = item_bbox[i]
        elif item_bbox:
            collection_bboxes.append(item_bbox)
        self._check_wgs84_compliance(collection_bboxes[0], "collection", self._collection.get("id"))

    def _update_collection_interval(self, stac_item: dict[str, Any]) -> None:
        if (datetime := stac_item["properties"].get("datetime")) is not None:
            item_interval = [datetime, datetime]
        else:
            item_interval = [stac_item["properties"][prop] for prop in ("start_datetime", "end_datetime")]
        collection_intervals = self._collection["extent"]["temporal"]["interval"]
        if collection_intervals:
            collection_interval = collection_intervals[0]
            if collection_interval[0] is not None and item_interval[0] < collection_interval[0]:
                collection_interval[0] = item_interval[0]
            if collection_interval[1] is not None and item_interval[1] > collection_interval[1]:
                collection_interval[1] = item_interval[1]
        else:
            collection_intervals.append(item_interval)

    def _update_collection_summaries(self, stac_item: dict[str, Any]) -> None:
        """
        Update the summaries value in the stac_collection based on the values in stac_item.

        This only creates summaries for simple types (strings, numbers, boolean) and does not
        create summaries as JSON schema objects.
        """
        if "summaries" not in self._collection:
            self._collection["summaries"] = {}
        elif "needs_summaries_update" in self._collection["summaries"]:
            self._collection["summaries"].pop("needs_summaries_update")
        summaries = self._collection["summaries"]
        for name, value in stac_item["properties"].items():
            summary = summaries.get(name)
            if name in self.exclude_summaries:
                continue
            elif isinstance(value, bool):
                if summary is None:
                    summaries[name] = [value]
                elif value not in summary:
                    summary.append(value)
            elif isinstance(value, str):
                try:
                    time_value = datetime.fromisoformat(value)
                except ValueError:
                    if summary is None:
                        summaries[name] = [value]
                    elif isinstance(summary, list):
                        if value not in summary:
                            summary.append(value)
                else:
                    if summary is None:
                        summaries[name] = {"minimum": value, "maximum": value}
                    elif summary.get("minimum") is not None and summary.get("maximum") is not None:
                        if time_value < datetime.fromisoformat(summary["minimum"]):
                            summary["minimum"] = value
                        elif time_value > datetime.fromisoformat(summary["maximum"]):
                            summary["maximum"] = value
            elif isinstance(value, (int, float)):
                if summary is None:
                    summaries[name] = {"minimum": value, "maximum": value}
                elif isinstance(summary, list):
                    # this property does not necessarily contain all numeric values
                    if value not in summary:
                        summary.append(value)
                elif summary.get("minimum") is not None and summary.get("maximum") is not None:
                    if value < summary["minimum"]:
                        summary["minimum"] = value
                    elif value > summary["maximum"]:
                        summary["maximum"] = value

    def _update_collection(self, stac_item: dict[str, Any]) -> None:
        if self.update:
            if self.update_collection in ("extents", "all"):
                LOGGER.info(
                    "Updating collection extents [%s] with data from item [%s]",
                    self._collection.get("id"),
                    stac_item.get("id"),
                )
                self._update_collection_bbox(stac_item)
                self._update_collection_interval(stac_item)
            if self.update_collection in ("summaries", "all"):
                LOGGER.info(
                    "Updating collection summaries [%s] with data from item [%s]",
                    self._collection.get("id"),
                    stac_item.get("id"),
                )
                self._update_collection_summaries(stac_item)

    def ingest(self) -> None:
        """Ingest data."""
        counter = 0
        failures = 0
        LOGGER.info("Data ingestion")
        for item_name, item_loc, item_data in self._ingest_pipeline:
            LOGGER.info(f"New data item: {item_name}", extra={"item_loc": item_loc})
            try:
                stac_item = self.create_stac_item(item_name, item_data)
            except Exception:
                LOGGER.exception(
                    f"Failed to create STAC item for {item_name}",
                    extra={"item_loc": item_loc, "loader": type(self._ingest_pipeline)},
                )
                failures += 1
                stac_item = None
            else:
                self._update_collection(stac_item)
            if stac_item:
                try:
                    post_stac_item(
                        self.stac_host,
                        self.collection_id,
                        item_name,
                        stac_item,
                        update=self.update,
                        session=self._session,
                    )
                except Exception:
                    # Something went wrong on the server side, most likely because the STAC item generated above has
                    # incorrect data. Writing the STAC item to file so that the issue could be diagnosed and fixed.
                    stac_output_fname = "error_STAC_rep_" + item_name.split(".")[0] + ".json"
                    json.dump(stac_item, open(stac_output_fname, "w"), indent=2)
                    LOGGER.exception(
                        f"Failed to post STAC item for {item_name}",
                        extra={
                            "item_loc": item_loc,
                            "loader": type(self._ingest_pipeline),
                            "stac_output_fname": stac_output_fname,
                        },
                    )
                    failures += 1

            counter += 1
            LOGGER.info(f"Processed {counter} data items. {failures} failures")
        if self.update and self.update_collection != "none":
            self.publish_stac_collection(self._collection)
