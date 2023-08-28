import re
from enum import Enum


def url_validate(target: str) -> bool:
    """Validate whether a supplied URL is reliably written.

    Parameters
    ----------
    target : str

    References
    ----------
    https://stackoverflow.com/a/7160778/7322852
    """
    url_regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        # domain...
        r"(?:(?:[A-Z\d](?:[A-Z\d-]{0,61}[A-Z\d])?\.)+(?:[A-Z]{2,6}\.?|[A-Z\d-]{2,}\.?)|"
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return True if re.match(url_regex, target) else False


def collection2enum(collection):
    """Create Enum based on terms from pyessv collection.

    Parameters
    ----------
    collection : pyessv.model.collection.Collection
      pyessv collection of terms.

    Returns
    -------
    Enum
      Enum storing terms and their labels from collection.
    """
    mp = {term.name: term.label for term in collection}
    return Enum(collection.raw_name.capitalize(), mp, module="base")
