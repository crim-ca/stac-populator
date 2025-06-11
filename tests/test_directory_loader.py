import abc
import argparse
import functools
import inspect
import json
import os
from typing import Any, Callable, Generator

import pystac
import pytest
import requests
import responses

from STACpopulator.cli import add_parser_args
from STACpopulator.cli import main as cli_main
from STACpopulator.implementations.DirectoryLoader import crawl_directory
from STACpopulator.input import STACDirectoryLoader

RequestContext = Generator[responses.RequestsMock, None, None]


@pytest.fixture(scope="session")
def file_id_map() -> dict[str, str]:
    return {
        "collection.json": "EuroSAT-subset-train",
        "item-0.json": "EuroSAT-subset-train-sample-0-class-AnnualCrop",
        "item-1.json": "EuroSAT-subset-train-sample-1-class-AnnualCrop",
        "nested/collection.json": "EuroSAT-subset-test",
        "nested/item-0.json": "EuroSAT-subset-test-sample-0-class-AnnualCrop",
        "nested/item-1.json": "EuroSAT-subset-test-sample-1-class-AnnualCrop",
        "nested2/item-2.json": "EuroSAT-subset-train-sample-2-class-AnnualCrop",
        "nested2/item-3.json": "EuroSAT-subset-train-sample-3-class-AnnualCrop",
    }


@pytest.fixture(scope="package")
def file_contents(file_id_map: dict[str, str], request: pytest.FixtureRequest) -> dict[str, bytes]:
    contents = {}
    for file_name in file_id_map:
        ref_file = os.path.join(request.fspath.dirname, "data/test_directory", file_name)
        with open(ref_file, mode="r", encoding="utf-8") as f:
            json_data = json.load(f)
            contents[file_name] = json.dumps(json_data, indent=None).encode()
    return contents


@pytest.fixture(autouse=True)
def request_mock(namespace: argparse.Namespace, file_id_map: dict[str, str]) -> RequestContext:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock_context:
        mock_context.add(
            "GET", namespace.stac_host, json={"stac_version": pystac.get_stac_version(), "type": "Catalog"}
        )
        mock_context.add(
            "POST",
            f"{namespace.stac_host}collections",
            headers={"Content-Type": "application/json"},
        )
        mock_context.add(
            "POST",
            f"{namespace.stac_host}collections/{file_id_map['collection.json']}/items",
            headers={"Content-Type": "application/json"},
        )
        mock_context.add(
            "POST",
            f"{namespace.stac_host}collections/{file_id_map['nested/collection.json']}/items",
            headers={"Content-Type": "application/json"},
        )
        yield mock_context


@pytest.mark.parametrize("prune_option", [True, False])
class _TestDirectoryLoader(abc.ABC):
    @abc.abstractmethod
    @pytest.fixture
    def namespace(self, *args: Any) -> argparse.Namespace:
        raise NotImplementedError

    @abc.abstractmethod
    @pytest.fixture
    def runner(self, *args: Any) -> Callable:
        raise NotImplementedError

    def test_runner(
        self,
        prune_option: bool,
        namespace: argparse.Namespace,
        file_id_map: dict[str, str],
        file_contents: dict[str, bytes],
        request_mock: RequestContext,
        runner: Callable,
    ):
        """
        This test is designed to read files from the data/test_directory.

        That directory contains files that are valid STAC items and collections
        and others that are not. Please see the "description" field of each file
        that contains "not-an-item" or "not-a-collection" in the file name to see
        what condition each file is testing.

        Also see the description in data/test_directory/nested2/collection.json
        which is a valid collection file name but with an invalid type.

        This test assumes that the default values for the collection_pattern and
        item_pattern arguments are used.
        """
        runner()

        assert len(request_mock.calls) == (4 if prune_option else 9)
        assert request_mock.calls[0].request.url == namespace.stac_host

        base_col = file_id_map["collection.json"]
        assert request_mock.calls[1].request.path_url == "/stac/collections"
        assert request_mock.calls[1].request.body == file_contents["collection.json"]

        # NOTE:
        #   Because directory crawler uses 'os.walk', loading order is OS-dependant.
        #   Since the order does not actually matter, consider item indices interchangeably.
        req3_json = json.loads(request_mock.calls[2].request.body.decode())
        req3_item = req3_json["id"]
        item0_idx, item1_idx = (2, 3) if "sample-0" in req3_item else (3, 2)

        assert request_mock.calls[item0_idx].request.path_url == f"/stac/collections/{base_col}/items"
        assert request_mock.calls[item0_idx].request.body == file_contents["item-0.json"]

        assert request_mock.calls[item1_idx].request.path_url == f"/stac/collections/{base_col}/items"
        assert request_mock.calls[item1_idx].request.body == file_contents["item-1.json"]

        if not prune_option:
            req5_json = json.loads(request_mock.calls[4].request.body.decode())
            req5_item = req5_json["id"]
            item2_idx, item3_idx = (4, 5) if "sample-2" in req5_item else (5, 4)

            assert request_mock.calls[item2_idx].request.path_url == f"/stac/collections/{base_col}/items"
            assert request_mock.calls[item2_idx].request.body == file_contents["nested2/item-2.json"]

            assert request_mock.calls[item3_idx].request.path_url == f"/stac/collections/{base_col}/items"
            assert request_mock.calls[item3_idx].request.body == file_contents["nested2/item-3.json"]

            # test that previous validation calls were cached properly
            assert request_mock.calls[6].request.url != namespace.stac_host

            nested_col = file_id_map["nested/collection.json"]
            assert request_mock.calls[6].request.path_url == "/stac/collections"
            assert request_mock.calls[6].request.body == file_contents["nested/collection.json"]

            # NOTE:
            #   Because directory crawler users 'os.walk', loading order is OS-dependant.
            #   Since the order does not actually matter, consider item indices interchangeably.
            req8_json = json.loads(request_mock.calls[7].request.body.decode())
            req8_item = req8_json["id"]
            item0_idx, item1_idx = (7, 8) if "sample-0" in req8_item else (8, 7)

            assert request_mock.calls[item0_idx].request.path_url == f"/stac/collections/{nested_col}/items"
            assert request_mock.calls[item0_idx].request.body == file_contents["nested/item-0.json"]

            assert request_mock.calls[item1_idx].request.path_url == f"/stac/collections/{nested_col}/items"
            assert request_mock.calls[item1_idx].request.body == file_contents["nested/item-1.json"]


class TestModule(_TestDirectoryLoader):
    @pytest.fixture
    def runner(self, namespace: argparse.Namespace) -> Callable:
        with requests.Session() as session:
            return functools.partial(crawl_directory.runner, namespace, session)

    @pytest.fixture
    def namespace(self, request: pytest.FixtureRequest, prune_option: bool) -> argparse.Namespace:
        dirloader_init_params = inspect.signature(STACDirectoryLoader.__init__).parameters
        return argparse.Namespace(
            verify=False,
            cert=None,
            auth_handler=None,
            stac_host="http://example.com/stac/",
            directory=os.path.join(request.fspath.dirname, "data/test_directory"),
            prune=prune_option,
            collection_pattern=dirloader_init_params["collection_pattern"].default,
            item_pattern=dirloader_init_params["item_pattern"].default,
            update=True,
            stac_version=None,
        )

    def test_set_stac_version(self, namespace, runner):
        if pystac.get_stac_version() == "1.0.0":
            namespace.stac_version = "1.1.0"
        else:
            namespace.stac_version = "1.0.0"
        with pytest.raises(RuntimeError):
            runner()
        assert pystac.get_stac_version() == namespace.stac_version


class TestFromCLI(_TestDirectoryLoader):
    @pytest.fixture
    def args(self, request: pytest.FixtureRequest, prune_option: bool) -> list[str]:
        cmd_args = [
            "--no-verify",
            "run",
            "DirectoryLoader",
            "http://example.com/stac/",
            os.path.join(request.fspath.dirname, "data/test_directory"),
            "--update",
        ]
        if prune_option:
            cmd_args.append("--prune")
        if request.node.get_closest_marker("set_stac_version"):
            if pystac.get_stac_version() == "1.0.0":
                stac_version = "1.1.0"
            else:
                stac_version = "1.0.0"
            cmd_args.extend(["--stac-version", stac_version])
        return cmd_args

    @pytest.fixture
    def runner(self, args: list[str]) -> int:
        return functools.partial(cli_main, *args)

    @pytest.fixture
    def namespace(self, args: tuple[str]) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        add_parser_args(parser)
        return parser.parse_args(args)

    @pytest.mark.set_stac_version
    def test_set_stac_version(self, runner):
        prev_stac_version = pystac.get_stac_version()
        with pytest.raises(RuntimeError):
            runner()
        assert prev_stac_version != pystac.get_stac_version()
