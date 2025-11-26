from typing import Any, Iterable, MutableMapping, Optional

from pytest import Session

from STACpopulator.collection_update import UpdateModesOptional
from STACpopulator.input import STACDirectoryLoader
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.populators.base import STACpopulatorBase


class DirectoryPopulator(STACpopulatorBase):
    """Populator that constructs STAC objects from files in a directory."""

    item_geometry_model = GeoJSONPolygon

    def __init__(
        self,
        stac_host: str,
        loader: STACDirectoryLoader,
        update: bool,
        collection: dict[str, Any],
        session: Optional[Session] = None,
        extra_item_parsers: Optional[list[str]] = None,
        extra_collection_parsers: Optional[list[str]] = None,
        extra_parser_arguments: Optional[dict[str, str] | list[tuple[str, str]]] = None,
        update_collection: UpdateModesOptional = "none",
        exclude_summaries: Iterable[str] = (),
    ) -> None:
        self._collection = collection
        super().__init__(
            stac_host,
            loader,
            update=update,
            session=session,
            extra_item_parsers=extra_item_parsers,
            extra_collection_parsers=extra_collection_parsers,
            extra_parser_arguments=extra_parser_arguments,
            update_collection=update_collection,
            exclude_summaries=exclude_summaries,
        )

    def load_config(self) -> MutableMapping[str, Any]:
        """Load configuration options."""
        self._collection_info = self._collection
        return self._collection_info

    def create_stac_collection(self) -> MutableMapping[str, Any]:
        """Return a STAC collection."""
        self.publish_stac_collection(self._collection_info)
        return self._collection_info

    def create_stac_item(self, item_name: str, item_data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        """Return a STAC item."""
        return item_data
