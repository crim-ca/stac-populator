def thredds_crawler(cat, depth=1):
    """Return a generator walking a THREDDS data catalog for datasets.

    Parameters
    ----------
    cat : TDSCatalog
      THREDDS catalog.
    depth : int
      Maximum recursive depth. Setting 0 will return only datasets within the top-level catalog. If None,
      depth is set to 1000.
    """
    yield from cat.datasets.items()
    if depth is None:
        depth = 1000

    if depth > 0:
        for name, ref in cat.catalog_refs.items():
            child = ref.follow()
            yield from thredds_crawler(child, depth=depth - 1)
