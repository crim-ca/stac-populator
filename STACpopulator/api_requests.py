import logging
import os
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from colorlog import ColoredFormatter

LOGGER = logging.getLogger(__name__)
LOGFORMAT = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s"
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setFormatter(formatter)
LOGGER.addHandler(stream)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def stac_host_reachable(url: str) -> bool:
    try:
        registry = requests.get(url)
        registry.raise_for_status()
        return True
    except (requests.exceptions.RequestException, requests.exceptions.ConnectionError):
        return False


def stac_collection_exists(stac_host: str, collection_id: str) -> bool:
    """
    Get a STAC collection

    Returns the collection JSON.
    """
    r = requests.get(os.path.join(stac_host, "collections", collection_id), verify=False)

    return r.status_code == 200


def post_stac_collection(stac_host: str, json_data: dict[str, Any], update: Optional[bool] = True) -> None:
    """
    Post a STAC collection.

    Returns the collection id.
    """
    collection_id = json_data["id"]
    r = requests.post(os.path.join(stac_host, "collections"), json=json_data, verify=False)

    if r.status_code == 200:
        LOGGER.info(f"Created STAC collection {collection_id}")
    elif r.status_code == 409:
        if update:
            LOGGER.info(f"STAC collection {collection_id} already exists. Updating.")
            r = requests.put(os.path.join(stac_host, "collections"), json=json_data, verify=False)
            r.raise_for_status()
        else:
            LOGGER.info(f"STAC collection {collection_id} already exists.")
    else:
        r.raise_for_status()


def post_stac_item(
    stac_host: str, collection_id: str, json_data: dict[str, dict], update: Optional[bool] = True
) -> bool:
    item_id = json_data["id"]

    r = requests.post(urljoin(stac_host, f"collections/{collection_id}/items"), json=json_data)

    if r.status_code == 200:
        LOGGER.info(f"Created item {item_id}")
    elif r.status_code == 409:
        if update:
            LOGGER.info(f"Item {item_id} already exists. Updating.")
            r = requests.put(urljoin(stac_host, f"collections/{collection_id}/items"), json=json_data)
            r.raise_for_status()
        else:
            LOGGER.info(f"Item {item_id} already exists.")
    else:
        r.raise_for_status()
