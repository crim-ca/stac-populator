import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Literal

import pystac
import requests
from pystac_client.stac_api_io import StacApiIO

from STACpopulator.api_requests import post_stac_collection

LOGGER = logging.getLogger(__name__)

UpdateModes = Literal["extents", "summaries", "all"]


def check_wgs84_compliance(bbox: list[int | float], stac_object_type: str, stac_object_id: str | None) -> None:
    """
    Display a warning if the bbox does not conform to WGS84.

    WGS84 requires longitude values to be between -180 and 180 (inclusive) and latitude values to be between
    -90 and 90 (inclusive).
    """
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


def sorted_bbox(bbox: list[int | float]) -> list[int | float]:
    """
    Return the bbox but sorted so that dimensional values are in sorted order.

    For example:

    >>> bbox = [1, 3, 5, 2, 0, 4]
    >>> sorted_bbox(bbox)
    [1, 0, 4, 2, 3, 5]
    """
    return [a for b in zip(*(sorted(axis) for axis in zip(bbox[: len(bbox) // 2], bbox[len(bbox) // 2 :]))) for a in b]


def update_collection_bbox(collection: dict, item: dict) -> None:
    """Update the spatial extent values in the collection based on the datetime properties in item."""
    item_bbox = item.get("bbox")
    if item_bbox is None:
        # bbox can be missing if there is no geometry
        return
    bbox = sorted_bbox(item_bbox)
    if item_bbox != bbox:
        LOGGER.warning(
            "STAC item with id [%s] contains a bbox with unsorted values: %s should be %s",
            item.get("id"),
            item_bbox,
            bbox,
        )
        item_bbox = bbox
    check_wgs84_compliance(item_bbox, "item", item.get("id"))
    collection_bboxes = collection["extent"]["spatial"]["bbox"]
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
    check_wgs84_compliance(collection_bboxes[0], "collection", collection.get("id"))


def update_collection_interval(collection: dict, item: dict) -> None:
    """Update the temporal extent values in the collection based on the datetime properties in item."""
    if (datetime := item["properties"].get("datetime")) is not None:
        item_interval = [datetime, datetime]
    else:
        item_interval = [item["properties"][prop] for prop in ("start_datetime", "end_datetime")]
    collection_intervals = collection["extent"]["temporal"]["interval"]
    if collection_intervals:
        collection_interval = collection_intervals[0]
        if collection_interval[0] is not None and item_interval[0] < collection_interval[0]:
            collection_interval[0] = item_interval[0]
        if collection_interval[1] is not None and item_interval[1] > collection_interval[1]:
            collection_interval[1] = item_interval[1]
    else:
        collection_intervals.append(item_interval)


def update_collection_summaries(collection: dict, item: dict, exclude_summaries: Iterable = ()) -> None:
    """
    Update the summaries value in the collection based on the values in item.

    This only creates summaries for simple types (strings, numbers, boolean) and does not
    create summaries as JSON schema objects.
    """
    if "summaries" not in collection:
        collection["summaries"] = {}
    elif "needs_summaries_update" in collection["summaries"]:
        collection["summaries"].pop("needs_summaries_update")
    summaries = collection["summaries"]
    # the STAC spec does not recommend including summaries that are covered by the extent already
    exclude_summaries = tuple(exclude_summaries) + ("datetime", "start_datetime", "end_datetime")
    for name, value in item["properties"].items():
        summary = summaries.get(name)
        if name in exclude_summaries:
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


def update_collection(mode: UpdateModes, collection: dict, item: dict, exclude_summaries: Iterable = ()) -> None:
    """
    Update various values in the collection based on the values in item.

    If mode is "extents", this will update temporal and spatial extents.

    If mode is "summaries", this will update summary values based on the item's properties except for the
    properties listed in exclude_summaries.

    If mode is "all", both extents and summaries will be updated.
    """
    if mode in ("extents", "all"):
        LOGGER.info(
            "Updating collection extents [%s] with data from item [%s]",
            collection.get("id"),
            item.get("id"),
        )
        update_collection_bbox(collection, item)
        update_collection_interval(collection, item)
    if mode in ("summaries", "all"):
        LOGGER.info(
            "Updating collection summaries [%s] with data from item [%s]",
            collection.get("id"),
            item.get("id"),
        )
        update_collection_summaries(collection, item, exclude_summaries)


def update_api_collection(
    mode: UpdateModes, collection_uri: str, exclude_summaries: Iterable, session: requests.Session
) -> None:
    """
    Update various values in the collection based on all of the items in the collection.

    The collection will be updated to the STAC API where the collection exists.

    If mode is "extents", this will update temporal and spatial extents.

    If mode is "summaries", this will update summary values based on the item's properties except for the
    properties listed in exclude_summaries.

    If mode is "all", both extents and summaries will be updated.
    """
    stac_api_io = StacApiIO()
    stac_api_io.session = session
    pystac_collection = pystac.Collection.from_file(collection_uri, stac_io=stac_api_io)
    # transforming hrefs is unnecessary for this operation and pystac makes additional requests to the API if True
    collection_dict = pystac_collection.to_dict(transform_hrefs=False)
    LOGGER.info("Updating collection located at '%s' with mode '%s'.", collection_uri, mode)
    for item in pystac_collection.get_items(recursive=True):
        LOGGER.info("Updating collection (id='%s') with values from item (id='%s')")
        update_collection(mode, collection_dict, item.to_dict(transform_hrefs=False), exclude_summaries)
    stac_root = pystac_collection.get_root_link()
    post_stac_collection(stac_root, collection_dict, update=True, session=session)
