import logging
import unittest.mock

import pystac
import pytest
import requests

from STACpopulator.collection_update import update_api_collection


@pytest.fixture
def stac_host():
    return "https://example.com/stac"


@pytest.fixture
def initial_collection_data(stac_host):
    return {
        "stac_version": pystac.get_stac_version(),
        "type": "Collection",
        "id": "test",
        "title": "test",
        "description": "test",
        "license": "MIT",
        "extent": {
            "spatial": {"bbox": [[-2.0, 0.0, 2.0, 3.0]]},
            "temporal": {"interval": [["2015-06-27T00:00:00Z", "2017-06-14T00:00:00Z"]]},
        },
        "links": [
            {"rel": "root", "href": stac_host, "type": "application/json"},
            {"rel": "self", "href": f"{stac_host}/collections/test", "type": "application/json"},
        ],
    }


@pytest.fixture
def initial_collection(initial_collection_data):
    return pystac.Collection.from_dict(initial_collection_data)


@pytest.fixture
def stac_items_data():
    return [
        {
            "stac_version": pystac.get_stac_version(),
            "type": "Feature",
            "id": f"test-{i}",
            "links": [],
            "assets": {},
            "bbox": data["bbox"],
            "properties": data["properties"],
            "geometry": {  # simple geometry because it doesn't matter (only bbox is used)
                "type": "Point",
                "coordinates": [0, 0],
            },
        }
        for i, data in enumerate(
            [
                {
                    "bbox": [-4, 1, 3, 2],
                    "properties": {"datetime": "2014-02-22T00:00:00Z", "string": "test1", "number": 3, "bool": False},
                },
                {
                    "bbox": [-1, 4, 1, -1],
                    "properties": {
                        "start_datetime": "2015-09-02T00:00:00Z",
                        "end_datetime": "2222-03-02T00:00:00Z",
                        "string": "test2",
                        "number": 10,
                        "bool": True,
                    },
                },
                {
                    "bbox": [0, 0, 0, 0],
                    "properties": {
                        "start_datetime": "2016-09-02T00:00:00Z",
                        "end_datetime": "2016-03-02T00:00:00Z",
                        "string": "test2",
                        "number": 10,
                        "bool": True,
                    },
                },
            ]
        )
    ]


@pytest.fixture
def stac_items(stac_items_data):
    return [pystac.Item.from_dict(data) for data in stac_items_data]


class TestUpdateAPICollection:
    @pytest.fixture(autouse=True)
    def patch_pystac_collection(self, initial_collection):
        with unittest.mock.patch.object(pystac.Collection, "from_file", return_value=initial_collection):
            yield

    @pytest.fixture(autouse=True)
    def patch_pystac_get_items(self, stac_items):
        with unittest.mock.patch("pystac.Collection.get_items", return_value=iter(stac_items)) as mock:
            yield mock

    @pytest.fixture(autouse=True)
    def post_collection_mock(self):
        with unittest.mock.patch("STACpopulator.collection_update.post_stac_collection") as mock:
            yield mock

    def get_updated(self, mode, post_collection_mock, exclude_summaries=()):
        update_api_collection(
            mode=mode, collection_uri="this is patched", exclude_summaries=exclude_summaries, session=requests.Session()
        )
        return post_collection_mock.call_args.args[1]

    @pytest.mark.parametrize("mode", ["all", "extents", "summaries"])
    def test_updated(self, post_collection_mock, mode):
        updated = self.get_updated(mode, post_collection_mock)
        if mode in ("extents", "all"):
            assert updated["extent"]["spatial"]["bbox"] == [[-4, -1, 3, 4]]
            assert updated["extent"]["temporal"]["interval"] == [["2014-02-22T00:00:00Z", "2222-03-02T00:00:00Z"]]
        if mode in ("summaries", "all"):
            assert updated["summaries"] == {
                "string": ["test1", "test2"],
                "number": {"maximum": 10, "minimum": 3},
                "bool": [False, True],
            }

    def test_summaries_not_updated(self, post_collection_mock):
        updated = self.get_updated("extents", post_collection_mock)
        assert "summaries" not in updated

    def test_extents_not_updated(self, post_collection_mock, initial_collection_data):
        updated = self.get_updated("summaries", post_collection_mock)
        assert updated["extent"] == initial_collection_data["extent"]

    @pytest.mark.parametrize("mode", ["all", "summaries"])
    def test_update_summaries_with_exclusions(self, post_collection_mock, mode):
        updated = self.get_updated(mode, post_collection_mock, exclude_summaries=["string", "bool"])
        assert updated["summaries"] == {"number": {"maximum": 10, "minimum": 3}}

    def test_sorted_bbox_warning(self, post_collection_mock, caplog):
        caplog.set_level(logging.WARNING)
        self.get_updated("extents", post_collection_mock)
        assert "contains a bbox with unsorted values" in caplog.text

    @pytest.mark.parametrize("bbox_update", enumerate([-200, -100, 200, 100]))
    def test_wgs84_compliance_warning(
        self, post_collection_mock, patch_pystac_get_items, stac_items, bbox_update, caplog
    ):
        caplog.set_level(logging.WARNING)
        stac_items[0].bbox[bbox_update[0]] = bbox_update[1]
        patch_pystac_get_items.return_value = iter(stac_items)
        self.get_updated("extents", post_collection_mock)
        assert "outside of the accepted range" in caplog.text
