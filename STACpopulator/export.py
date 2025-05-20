import json
import logging
import os
import pathlib
from typing import Iterable, cast

import pystac
import pystac_client
import pystac_client.client
import pystac_client.exceptions
import requests
from pystac_client.stac_api_io import StacApiIO

LOGGER = logging.getLogger(__name__)


class Client(pystac_client.Client):
    """
    A Client for interacting with the root of a STAC Catalog or API.

    This inherits most methods from the pystac_client.Client class and extends
    others to ensure that Catalogs and APIs that misreport their conformance
    classes can still be exported.
    """

    def get_children(self) -> Iterable[pystac_client.Client | pystac_client.CollectionClient]:
        """
        Return all children of this catalog.

        If a catalog reports that they conform to the COLLECTIONS conformance class but do
        not provide a valid /collections endpoint, this will fall back to discovering collections
        from the catalog's links instead of raising an error.
        """
        collection_ids = set()
        try:
            for collection in self.get_collections():
                collection_ids.add(collection.id)
                yield collection
        except pystac_client.exceptions.APIError:
            self.remove_conforms_to("COLLECTIONS")
            yield from super().get_children()
        else:
            for catalog in self.get_stac_objects(rel=pystac.RelType.CHILD, typ=pystac.Catalog):
                catalog = cast(pystac.Catalog, catalog)
                if catalog.id not in collection_ids:
                    yield catalog

    def search(self, *args, **kwargs) -> pystac_client.ItemSearch:
        """
        Query the /search endpoint for all items that are direct descendants of this catalog.

        This is no longer necessary when https://github.com/stac-utils/pystac-client/issues/798
        has been resolved.
        """
        kwargs["collections"] = self.id
        return super().search(*args, **kwargs)

    def get_items(self, *ids: str, recursive: bool | None = None) -> Iterable[pystac.Item]:
        """
        Return all items of this catalog.

        If a catalog reports that they conform to the ITEM_SEARCH conformance class but do
        not provide a valid /search endpoint, this will fall back to discovering items
        from the catalog's links instead of raising an error.
        """
        try:
            yield from super().get_items(*ids, recursive=recursive)
        except pystac_client.exceptions.APIError:
            self.remove_conforms_to("ITEM_SEARCH")
            yield from super().get_items(*ids, recursive=recursive)


# Ensure that nested catalogs use our updated Client class
pystac_client.client.Client = Client


def _export_catalog(
    client: Client | pystac_client.CollectionClient, directory: pathlib.Path, resume: bool = False
) -> None:
    directory /= client.id
    file_name = "catalog.json" if isinstance(client, Client) else "collection.json"
    collection_type = file_name.split(".")[0].capitalize()
    if not resume and directory.exists():
        n_duplicates = sum(1 for _ in directory.parent.glob(f"{client.id}*/"))
        directory = directory.parent / f"{client.id}-duplicate-id-{n_duplicates}"
        LOGGER.warning(
            "%s with ID %s already exists in this catalog. IDs should be unique!", collection_type, client.id
        )
    directory.mkdir(exist_ok=True, parents=True)
    with open(directory / file_name, "w", encoding="utf-8") as f:
        json.dump(client.to_dict(transform_hrefs=False), f)
    for item in client.get_items(recursive=False):
        with open(directory / f"item-{item.id}.json", "w", encoding="utf-8") as f:
            json.dump(item.to_dict(transform_hrefs=False), f)
    for child in client.get_children():
        _export_catalog(child, directory, resume=resume)


def export_catalog(directory: os.PathLike, stac_host: str, session: requests.Session, resume: bool = False) -> None:
    """Export a STAC catalog to files on disk."""
    stac_api_io = StacApiIO()
    stac_api_io.session = session
    directory = pathlib.Path(directory)
    client = Client.open(stac_host, stac_io=stac_api_io)
    _export_catalog(client, directory, resume)
