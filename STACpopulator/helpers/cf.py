import functools
from typing import Any, Dict, List

from STACpopulator.extensions.cf import CFExtension, CFParameter, T
from STACpopulator.helpers.base import ExtensionHelper


class CFHelper(ExtensionHelper):
    """CFHelper."""

    _prefix: str = "cf"
    variables: Dict[str, Any]

    @functools.cached_property
    def parameters(self) -> List[CFParameter]:
        """Extracts cf:parameter-like information from item_data."""
        parameters = []

        for var in self.variables.values():
            attrs = var.get("attributes", {})
            name = attrs.get("standard_name")  # Get the required standard name
            if not name:
                continue  # Skip if no valid name
            unit = attrs.get("units", "")
            parameters.append(CFParameter(name=name, unit=unit))

        return parameters

    @classmethod
    def from_data(
        cls,
        data: dict[str, Any],
        **kwargs,
    ) -> "CFHelper":
        """Create a CFHelper instance from raw data."""
        return cls(variables=data["data"]["variables"], **kwargs)

    def apply(self, item: T, add_if_missing: bool = True) -> T:
        """Apply the Datacube extension to an item."""
        ext = CFExtension.ext(item, add_if_missing=add_if_missing)
        ext.apply(parameters=self.parameters)

        # FIXME: This temporary workaround has been added to comply with the (most certainly buggy) validation schema for CF extension
        # It should be remove once the PR is integrated since applying on the item should be enough
        asset = item.assets["HTTPServer"]
        cf_asset_ext = CFExtension.ext(asset, add_if_missing=True)
        cf_asset_ext.apply(parameters=self.parameters)
        return item
