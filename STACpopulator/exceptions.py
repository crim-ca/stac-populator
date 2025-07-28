class STACPopulatorError(Exception):
    """STAC populator Error."""

    pass


class ExtensionLoadError(STACPopulatorError):
    """Extension Loading Error."""

    pass


class FunctionLoadError(STACPopulatorError):
    """External function loading error."""

    pass
