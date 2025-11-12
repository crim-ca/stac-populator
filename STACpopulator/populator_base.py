import functools
import importlib
import importlib.util
import inspect
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, MutableMapping, Optional, Type, Union

import pystac
from requests.sessions import Session

from STACpopulator.api_requests import (
    post_stac_collection,
    post_stac_item,
    stac_host_reachable,
    stac_version_match,
)
from STACpopulator.collection_update import UpdateModesOptional, update_collection
from STACpopulator.exceptions import FunctionLoadError
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
        extra_item_parsers: Optional[list[str]] = None,
        extra_collection_parsers: Optional[list[str]] = None,
        extra_parser_arguments: Optional[dict[str, str] | list[tuple[str, str]]] = None,
        update_collection: UpdateModesOptional = "none",
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
        extra_parser_arguments = dict(extra_parser_arguments or {})
        self._extra_item_parsers = [
            self._load_extra_parser(parser, extra_parser_arguments) for parser in (extra_item_parsers or [])
        ]
        self._extra_collection_parsers = [
            self._load_extra_parser(parser, extra_parser_arguments) for parser in (extra_collection_parsers or [])
        ]

        if extra_parser_arguments and not (self._extra_collection_parsers or self._extra_item_parsers):
            LOGGER.warning(
                "extra_parser_arguments will be ignored because no extra collection or item parsers are specified."
            )

        self.load_config()

        self._ingest_pipeline = data_loader
        self._stac_host = self.validate_host(stac_host)
        self.update = update
        self.update_collection = update_collection
        self.exclude_summaries = exclude_summaries

        LOGGER.info("Initialization complete")
        LOGGER.info(f"Collection {self.collection_name} is assigned ID {self.collection_id}")
        self._collection = self.create_stac_collection()

    @staticmethod
    def _load_extra_parser(func_str: str, extra_kwargs: dict[str, str]) -> Callable:
        if ":" in func_str:
            mod, func = func_str.split(":", 1)
            if mod.endswith(".py"):
                mod_name = re.sub(r"\W", "_", os.path.splitext(os.path.basename(mod))[0])
                mod_spec = importlib.util.spec_from_file_location(mod_name, mod)
                function_ns = importlib.util.module_from_spec(mod_spec)
                try:
                    mod_spec.loader.exec_module(function_ns)
                except FileNotFoundError as e:
                    raise FunctionLoadError(f"Unable to load python module from file: '{mod}'") from e
            else:
                try:
                    function_ns = importlib.import_module(mod)
                except ModuleNotFoundError as e:
                    raise FunctionLoadError(f"Unable to load module '{mod}'") from e
            try:
                callable_func = getattr(function_ns, func)
            except AttributeError as e:
                raise FunctionLoadError(f"Unable to load function '{func}' from '{mod}'") from e
            arg_spec = inspect.getfullargspec(callable_func)
            if arg_spec.varkw:
                return functools.partial(callable_func, **extra_kwargs)
            all_kwargs = arg_spec.args + arg_spec.kwonlyargs
            return functools.partial(callable_func, **{k: v for k, v in extra_kwargs.items() if k in all_kwargs})
        else:
            raise FunctionLoadError(
                "Parser function string is not properly formatted. Should be in the form 'module:function_name'"
            )

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
        for func in self._extra_collection_parsers:
            func(collection_data)
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

    def _update_collection(self, stac_item: dict[str, Any]) -> None:
        if self.update and self.update_collection != "none":
            update_collection(self.update_collection, self._collection, stac_item, self.exclude_summaries)

    def ingest(self) -> None:
        """Ingest data."""
        counter = 0
        failures = 0
        LOGGER.info("Data ingestion")
        for item_name, item_loc, item_data in self._ingest_pipeline:
            LOGGER.info(f"New data item: {item_name}", extra={"item_loc": item_loc})
            try:
                stac_item = self.create_stac_item(item_name, item_data)
                for func in self._extra_item_parsers:
                    func(stac_item)
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
