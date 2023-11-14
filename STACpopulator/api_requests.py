import logging
import os
from typing import Any, Optional

import requests
from requests import Session
from colorlog import ColoredFormatter

LOGGER = logging.getLogger(__name__)
LOGFORMAT = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s"
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setFormatter(formatter)
LOGGER.addHandler(stream)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def stac_host_reachable(url: str, session: Optional[Session] = None) -> bool:
    try:
        session = session or requests
        response = session.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        body = response.json()
        if body["type"] == "Catalog" and "stac_version" in body:
            return True
    except (requests.exceptions.RequestException, requests.exceptions.ConnectionError) as exc:
        LOGGER.error("Could not validate STAC host. Not reachable [%s] due to [%s]", url, exc, exc_info=exc)
    return False


def stac_collection_exists(stac_host: str, collection_id: str, session: Optional[Session] = None) -> bool:
    """
    Get a STAC collection

    Returns the collection JSON.
    """
    session = session or requests
    r = session.get(os.path.join(stac_host, "collections", collection_id), verify=False)
    return r.status_code == 200


def post_stac_collection(
    stac_host: str,
    json_data: dict[str, Any],
    update: Optional[bool] = True,
    session: Optional[Session] = None,
) -> None:
    """Post/create a collection on the STAC host

    :param stac_host: address of the STAC host
    :type stac_host: str
    :param json_data: JSON representation of the STAC collection
    :type json_data: dict[str, Any]
    :param update: if True, update the collection on the host server if it is already present, defaults to True
    :type update: Optional[bool], optional
    :param session: Session with additional configuration to perform requests.
    """
    session = session or requests
    collection_id = json_data["id"]
    collection_url = os.path.join(stac_host, "collections")
    r = session.post(collection_url, json=json_data)

    if r.status_code == 200:
        LOGGER.info(f"Collection {collection_id} successfully created")
    elif r.status_code == 409:
        if update:
            LOGGER.info(f"Collection {collection_id} already exists. Updating.")
            r = session.put(os.path.join(stac_host, "collections"), json=json_data)
            r.raise_for_status()
        else:
            LOGGER.info(f"Collection {collection_id} already exists.")
    else:
        r.raise_for_status()


def post_stac_item(
    stac_host: str,
    collection_id: str,
    item_name: str,
    json_data: dict[str, dict],
    update: Optional[bool] = True,
    session: Optional[Session] = None,
) -> None:
    """Post a STAC item to the host server.

    :param stac_host: address of the STAC host
    :type stac_host: str
    :param collection_id: ID of the collection to which to post this item
    :type collection_id: str
    :param item_name: name of the STAC item
    :type item_name: str
    :param json_data: JSON representation of the STAC item
    :type json_data: dict[str, dict]
    :param update: if True, update the item on the host server if it is already present, defaults to True
    :type update: Optional[bool], optional
    :param session: Session with additional configuration to perform requests.
    """
    session = session or requests
    item_id = json_data["id"]
    item_url = os.path.join(stac_host, f"collections/{collection_id}/items")
    r = session.post(item_url, json=json_data)

    if r.status_code == 200:
        LOGGER.info(f"Item {item_name} successfully added")
    elif r.status_code == 409:
        if update:
            LOGGER.info(f"Item {item_id} already exists. Updating.")
            r = session.put(os.path.join(stac_host, f"collections/{collection_id}/items/{item_id}"), json=json_data)
            r.raise_for_status()
        else:
            LOGGER.info(f"Item {item_id} already exists.")
    else:
        r.raise_for_status()
