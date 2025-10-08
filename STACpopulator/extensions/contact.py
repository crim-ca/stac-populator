"""Contact data model."""

from dataclasses import dataclass, field
from typing import List, Optional

import pystac
from dataclasses_json import LetterCase, config, dataclass_json

SCHEMA_URI = "https://stac-extensions.github.io/contacts/v0.1.1/schema.json"


@dataclass_json
@dataclass
class Info:
    """Gives contact information for and their "roles"."""

    value: str
    """The actual contact information, e.g. the phone number or the email address."""

    roles: Optional[List[str]] = None
    """The type(s) of this contact information, e.g. whether it's at work or at home."""


@dataclass_json
@dataclass
class Address:
    """Physical location at which contact can be made."""

    deliveryPoint: Optional[List[str]] = field(metadata=config(letter_case=LetterCase.CAMEL), default=None)
    """Address lines for the location, for example a street name and a house number."""

    city: Optional[str] = None
    """City for the location."""

    administrativeArea: Optional[str] = field(metadata=config(letter_case=LetterCase.CAMEL), default=None)
    """State or province of the location."""

    postalCode: Optional[str] = field(metadata=config(letter_case=LetterCase.CAMEL), default=None)
    """	ZIP or other postal code."""

    country: Optional[str] = None
    """Country of the physical address."""


@dataclass_json
@dataclass
class Contact:
    """Provides information about a contact."""

    name: Optional[str] = None
    """The name of the responsible person. Required if organization is missing."""

    organization: Optional[str] = None
    """Organization or affiliation of the contact. Required if name is missing"""

    identifier: Optional[str] = None
    """A value uniquely identifying the contact."""

    position: Optional[str] = None
    """The name of the role or position of the responsible person."""

    description: Optional[str] = None
    """Detailed multi-line description to fully explain the STAC entity."""

    logo: Optional[pystac.Link] = None
    """Graphic identifying the contact."""

    phones: Optional[List[Info]] = None
    """Telephone numbers at which contact can be made."""

    emails: Optional[List[Info]] = None
    """Email address at which contact can be made."""

    addresses: Optional[List[Address]] = None
    """Physical location at which contact can be made."""

    links: Optional[List[pystac.Link]] = None
    """Links related to the contact."""

    contactInstructions: Optional[str] = field(metadata=config(letter_case=LetterCase.CAMEL), default=None)
    """Supplemental instructions on how or when to contact the responsible party."""

    roles: Optional[List[str]] = None
    """The set of named duties, job functions and/or permissions associated with this contact."""
