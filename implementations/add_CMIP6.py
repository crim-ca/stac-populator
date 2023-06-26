import argparse
import logging

from colorlog import ColoredFormatter

from STACpopulator import STACpopulatorBase
from STACpopulator.crawlers import thredds_crawler

# from STACpopulator.metadata_parsers import nc_attrs_from_ncml

LOGGER = logging.getLogger(__name__)
LOGFORMAT = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s"
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setFormatter(formatter)
LOGGER.addHandler(stream)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


class CMIP6populator(STACpopulatorBase):
    def __init__(
        self,
        catalog: str,
        hostname: str,
        config: str,
    ) -> None:
        super().__init__(catalog, hostname, config, thredds_crawler, crawler_args={"depth": None})

    def process_STAC_item(self):  # noqa N802
        # TODO: next step is to implement this
        print("here")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="CMIP6 STAC populator")
    parser.add_argument("hostname", type=str, help="STAC API address")
    parser.add_argument("catalog_URL", type=str, help="URL to the CMIP6 thredds catalog")
    parser.add_argument("config_file", type=str, help="Name of the configuration file")

    args = parser.parse_args()
    LOGGER.info(f"Arguments to call: {args}")
    c = CMIP6populator(args.catalog_URL, args.hostname, args.config_file)
    c.ingest()
