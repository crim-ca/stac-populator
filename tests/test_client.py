from pystac_client import Client

def test_cmip6():
    """Assume some CMIP6 has been ingested."""
    c = Client.open("http://localhost:8880/stac")
