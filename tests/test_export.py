import json

import pystac_client
import pytest
import requests

from STACpopulator.export import export_catalog


@pytest.fixture
def catalog_api_info():
    url = "https://hirondelle.crim.ca/stac"
    file_structure = {
        "stac-fastapi",
        "stac-fastapi/0798aa197d54eb4332767a5a4077fb0f",
        "stac-fastapi/EuroSAT-full-validate",
        "stac-fastapi/c604ffb6d610adbb9a6b4787db7b8fd7",
        "stac-fastapi/EuroSAT-full-train",
        "stac-fastapi/EuroSAT-full-test",
        "stac-fastapi/EuroSAT-subset-test",
        "stac-fastapi/montreal_2023",
        "stac-fastapi/catalog.json",
        "stac-fastapi/newyork_2024",
        "stac-fastapi/EuroSAT-subset-train",
        "stac-fastapi/EuroSAT-subset-validate",
        "stac-fastapi/EuroSAT-subset-validate/collection.json",
        "stac-fastapi/EuroSAT-subset-validate/item-EuroSAT-subset-validate-sample-19-class-SeaLake.json",
        "stac-fastapi/EuroSAT-subset-train/collection.json",
        "stac-fastapi/EuroSAT-subset-train/item-EuroSAT-subset-train-sample-59-class-SeaLake.json",
        "stac-fastapi/newyork_2024/collection.json",
        "stac-fastapi/newyork_2024/item-wildfire_timestamp_2024_06_30_12_00_00.json",
        "stac-fastapi/montreal_2023/collection.json",
        "stac-fastapi/montreal_2023/item-wildfire_timestamp_2023_08_30_12_00_00.json",
        "stac-fastapi/EuroSAT-subset-test/collection.json",
        "stac-fastapi/EuroSAT-subset-test/item-EuroSAT-subset-test-sample-19-class-SeaLake.json",
        "stac-fastapi/EuroSAT-full-test/collection.json",
        "stac-fastapi/EuroSAT-full-test/item-EuroSAT-full-test-sample-5399-class-SeaLake.json",
        "stac-fastapi/EuroSAT-full-train/collection.json",
        "stac-fastapi/EuroSAT-full-train/item-EuroSAT-full-train-sample-16199-class-SeaLake.json",
        "stac-fastapi/c604ffb6d610adbb9a6b4787db7b8fd7/item-8644ba4c3d765b74cb50472e08063f26.json",
        "stac-fastapi/c604ffb6d610adbb9a6b4787db7b8fd7/collection.json",
        "stac-fastapi/EuroSAT-full-validate/item-EuroSAT-full-validate-sample-5399-class-SeaLake.json",
        "stac-fastapi/EuroSAT-full-validate/collection.json",
        "stac-fastapi/0798aa197d54eb4332767a5a4077fb0f/collection.json",
        "stac-fastapi/0798aa197d54eb4332767a5a4077fb0f/item-8a6add1935c993b57c6c6ca91f31310b.json",
    }
    return (url, file_structure)


@pytest.fixture
def catalog_nested_info():
    url = "https://asc-jupiter.s3.us-west-2.amazonaws.com/catalog.json"
    file_structure = {
        "usgs_jupiter_catalog",
        "usgs_jupiter_catalog/catalog.json",
        "usgs_jupiter_catalog/usgs_europa_catalog",
        "usgs_jupiter_catalog/usgs_europa_catalog/catalog.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/catalog.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/catalog.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_equi",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_equi/collection.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_equi/item-s0349875100.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_npola",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_npola/collection.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_npola/item-s0349875100.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_spola",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_spola/collection.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog-duplicate-id-1/usgs_controlled_images_voy1_voy2_galileo_spola/item-s0360063900.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/catalog.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_equi",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_equi/collection.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_equi/item-10ESGLOBAL01.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_npola",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_npola/collection.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_npola/item-14ESGLOCOL01.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_spola",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_spola/collection.json",
        "usgs_jupiter_catalog/usgs_europa_catalog/usgs_galileo_catalog/usgs_galileo_controlled_images_catalog/usgs_controlled_mosaics_voy1_voy2_galileo_spola/item-10ESGLOBAL01.json",
    }
    return url, file_structure


def _test_file_types(tmp_path):
    for file in tmp_path.rglob("*"):
        if file.is_file():
            with open(file) as f:
                data = json.load(f)
            if file.name == "catalog.json":
                assert data["type"] == "Catalog"
            elif file.name == "collection.json":
                assert data["type"] == "Collection"
            else:
                assert data["type"] == "Feature"


@pytest.mark.vcr
def test_export_api(tmp_path, catalog_api_info):
    url, expected = catalog_api_info
    with requests.Session() as session:
        export_catalog(tmp_path, url, session)
    assert expected == {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")}
    _test_file_types(tmp_path)


@pytest.mark.vcr
def test_export_catalog_nested(tmp_path, catalog_nested_info):
    url, expected = catalog_nested_info
    with (
        requests.Session() as session,
        pytest.warns((pystac_client.warnings.FallbackToPystac, pystac_client.warnings.NoConformsTo)),
    ):
        export_catalog(tmp_path, url, session)
    assert expected == {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")}
    _test_file_types(tmp_path)
