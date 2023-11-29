import argparse
import json
import os
import pytest
import responses

from STACpopulator.implementations.DirectoryLoader import crawl_directory

CUR_DIR = os.path.dirname(__file__)


@pytest.mark.parametrize(
    "prune_option",
    [True, False]
)
def test_directory_loader_populator_runner(prune_option: bool):
    ns = argparse.Namespace()
    stac_host = "http://test-host.com/stac/"
    setattr(ns, "verify", False)
    setattr(ns, "cert", None)
    setattr(ns, "auth_handler", None)
    setattr(ns, "stac_host", stac_host)
    setattr(ns, "directory", os.path.join(CUR_DIR, "data/test_directory"))
    setattr(ns, "prune", prune_option)
    setattr(ns, "update", True)

    file_id_map = {
        "collection.json": "EuroSAT-subset-train",
        "item-0.json": "EuroSAT-subset-train-sample-0-class-AnnualCrop",
        "item-1.json": "EuroSAT-subset-train-sample-1-class-AnnualCrop",
        "nested/collection.json": "EuroSAT-subset-test",
        "nested/item-0.json": "EuroSAT-subset-test-sample-0-class-AnnualCrop",
        "nested/item-1.json": "EuroSAT-subset-test-sample-1-class-AnnualCrop",
    }
    file_contents = {}
    for file_name in file_id_map:
        ref_file = os.path.join(CUR_DIR, "data/test_directory", file_name)
        with open(ref_file, mode="r", encoding="utf-8") as f:
            json_data = json.load(f)
            file_contents[file_name] = json.dumps(json_data, indent=None).encode()

    with responses.RequestsMock(assert_all_requests_are_fired=False) as request_mock:
        request_mock.add("GET", stac_host, json={"stac_version": "1.0.0", "type": "Catalog"})
        request_mock.add(
            "POST",
            f"{stac_host}collections",
            headers={"Content-Type": "application/json"},
        )
        request_mock.add(
            "POST",
            f"{stac_host}collections/{file_id_map['collection.json']}/items",
            headers={"Content-Type": "application/json"},
        )
        request_mock.add(
            "POST",
            f"{stac_host}collections/{file_id_map['nested/collection.json']}/items",
            headers={"Content-Type": "application/json"},
        )

        crawl_directory.runner(ns)

        assert len(request_mock.calls) == (4 if prune_option else 8)
        assert request_mock.calls[0].request.url == stac_host

        base_col = file_id_map['collection.json']
        assert request_mock.calls[1].request.path_url == "/stac/collections"
        assert request_mock.calls[1].request.body == file_contents["collection.json"]

        # NOTE:
        #   Because directory crawler users 'os.walk', loading order is OS-dependant.
        #   Since the order does not actually matter, consider item indices interchangeably.
        req0_json = json.loads(request_mock.calls[2].request.body.decode())
        req0_item = req0_json["id"]
        item0_idx, item1_idx = (2, 3) if "sample-0" in req0_item else (3, 2)

        assert request_mock.calls[item0_idx].request.path_url == f"/stac/collections/{base_col}/items"
        assert request_mock.calls[item0_idx].request.body == file_contents["item-0.json"]

        assert request_mock.calls[item1_idx].request.path_url == f"/stac/collections/{base_col}/items"
        assert request_mock.calls[item1_idx].request.body == file_contents["item-1.json"]

        if not prune_option:
            assert request_mock.calls[4].request.url == stac_host

            nested_col = file_id_map["nested/collection.json"]
            assert request_mock.calls[5].request.path_url == "/stac/collections"
            assert request_mock.calls[5].request.body == file_contents["nested/collection.json"]

            # NOTE:
            #   Because directory crawler users 'os.walk', loading order is OS-dependant.
            #   Since the order does not actually matter, consider item indices interchangeably.
            req0_json = json.loads(request_mock.calls[6].request.body.decode())
            req0_item = req0_json["id"]
            item0_idx, item1_idx = (6, 7) if "sample-0" in req0_item else (7, 6)

            assert request_mock.calls[item0_idx].request.path_url == f"/stac/collections/{nested_col}/items"
            assert request_mock.calls[item0_idx].request.body == file_contents["nested/item-0.json"]

            assert request_mock.calls[item1_idx].request.path_url == f"/stac/collections/{nested_col}/items"
            assert request_mock.calls[item1_idx].request.body == file_contents["nested/item-1.json"]
