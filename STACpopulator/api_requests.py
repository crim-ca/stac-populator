import os
from typing import Any

import requests


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


def post_stac_collection(stac_host: str, json_data: dict[str, Any]) -> None:
    """
    Post a STAC collection.

    Returns the collection id.
    """
    collection_id = json_data["id"]
    r = requests.post(os.path.join(stac_host, "collections"), json=json_data, verify=False)

    if r.status_code == 200:
        print(
            f"{bcolors.OKGREEN}[INFO] Pushed STAC collection [{collection_id}] to [{stac_host}] ({r.status_code}){bcolors.ENDC}"
        )
    elif r.status_code == 409:
        print(
            f"{bcolors.WARNING}[INFO] STAC collection [{collection_id}] already exists on [{stac_host}] ({r.status_code}), updating..{bcolors.ENDC}"
        )
        r = requests.put(os.path.join(stac_host, "collections"), json=json_data, verify=False)
        r.raise_for_status()
    else:
        r.raise_for_status()


def post_stac_item(stac_host: str, collection_id: str, data: dict[str, dict]) -> bool:
    pass