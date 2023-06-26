import lxml.etree
import requests


def nc_attrs_from_ncml(url):
    """Extract attributes from NcML file.

    Parameters
    ----------
    url : str
    Link to NcML service of THREDDS server for a dataset.

    Returns
    -------
    dict
    Global attribute values keyed by facet names, with variable attributes in `__variable__` nested dict, and
    additional specialized attributes in `__group__` nested dict.
    """
    parser = lxml.etree.XMLParser(encoding="UTF-8")

    ns = {"ncml": "http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2"}

    # Parse XML content - UTF-8 encoded documents need to be read as bytes
    xml = requests.get(url).content
    doc = lxml.etree.fromstring(xml, parser=parser)
    nc = doc.xpath("/ncml:netcdf", namespaces=ns)[0]

    # Extract global attributes
    out = _attrib_to_dict(nc.xpath("ncml:attribute", namespaces=ns))

    # Extract group attributes
    gr = {}
    for group in nc.xpath("ncml:group", namespaces=ns):
        gr[group.attrib["name"]] = _attrib_to_dict(group.xpath("ncml:attribute", namespaces=ns))

    # Extract variable attributes
    va = {}
    for variable in nc.xpath("ncml:variable", namespaces=ns):
        if "_CoordinateAxisType" in variable.xpath("ncml:attribute/@name", namespaces=ns):
            continue
        va[variable.attrib["name"]] = _attrib_to_dict(variable.xpath("ncml:attribute", namespaces=ns))

    out["__group__"] = gr
    out["__variable__"] = va

    return out


def _attrib_to_dict(elems):
    """Convert element attributes to dictionary.

    Ignore attributes with names starting with _
    """
    hidden_prefix = "_"
    out = {}
    for e in elems:
        a = e.attrib
        if a["name"].startswith(hidden_prefix):
            continue
        out[a["name"]] = a["value"]
    return out
