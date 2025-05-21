import json
import logging
import os
import pathlib
import time
from typing import Iterable, cast

import pystac
import pystac_client
import pystac_client.client
import pystac_client.exceptions
import requests
from pystac_client.stac_api_io import StacApiIO

LOGGER = logging.getLogger(__name__)


class DuplicateIDError(Exception):
    """Duplicate ID Error."""


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


def _write_stac_data(
    file: pathlib.Path,
    data: dict,
    start_time: int,
    create_parent: bool = False,
    resume: bool = False,
    ignore_duplicate_ids: bool = False,
) -> None:
    """
    Write STAC data to a file.

    If the file already exists and it hasn't been modified since the export started: raise an error or warning to tell
    the user that the catalog or collection contains STAC objects with non-unique IDs.

    If the file already exists and was created by a previous export: raise an error unless resume is True.

    Warning: if the file is modified by an external process after the export has already started, we cannot determine
    whether a file contains a non-unique STAC object (i.e. this does not attempt to lock the file).
    """
    if file.exists():
        if start_time < file.stat().st_mtime:
            msg = (
                f"{data['type']} with ID {data['id']} already exists in directory {file.parent}. IDs should be unique!"
            )
            if ignore_duplicate_ids:
                LOGGER.warning(msg)
                n_duplicates = sum(1 for _ in file.parent.glob(f"{file.name}.[0-9]*"))
                file = file.parent / f"{file.name}.{n_duplicates + 1}"
            else:
                raise DuplicateIDError(msg)
        elif not resume:
            raise FileExistsError(file)
    if create_parent:
        file.parent.mkdir(exist_ok=True)
    with open(file, mode="w", encoding="utf-8") as f:
        json.dump(data, f)


def _export_catalog(
    client: Client | pystac_client.CollectionClient,
    directory: pathlib.Path,
    start_time: int,
    resume: bool = False,
    ignore_duplicate_ids: bool = False,
) -> None:
    """
    Export a STAC catalog or collection to files on disk.

    This is a recursive helper function initiated by the export_catalog function.
    """
    directory /= client.id
    file_name = "catalog.json" if isinstance(client, Client) else "collection.json"
    _write_stac_data(
        directory / file_name, client.to_dict(transform_hrefs=False), start_time, True, resume, ignore_duplicate_ids
    )
    for item in client.get_items(recursive=False):
        _write_stac_data(
            directory / f"item-{item.id}.json",
            item.to_dict(transform_hrefs=False),
            start_time,
            False,
            resume,
            ignore_duplicate_ids,
        )
    for child in client.get_children():
        _export_catalog(child, directory, start_time, resume, ignore_duplicate_ids)


def export_catalog(
    directory: os.PathLike,
    stac_host: str,
    session: requests.Session,
    resume: bool = False,
    ignore_duplicate_ids: bool = False,
) -> None:
    """Export a STAC catalog to files on disk."""
    stac_api_io = StacApiIO()
    stac_api_io.session = session
    directory = pathlib.Path(directory)
    client = Client.open(stac_host, stac_io=stac_api_io)
    start_time = time.time()
    _export_catalog(client, directory, start_time, resume, ignore_duplicate_ids)
