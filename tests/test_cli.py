import os
import pkgutil
import re
import subprocess
import tempfile
from typing import Mapping

import pytest

from STACpopulator import implementations


def run_cli(*args: str, **kwargs: Mapping) -> subprocess.CompletedProcess:
    return subprocess.run(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, **kwargs)


@pytest.fixture(scope="session")
def populator_names():
    return {m.name for m in pkgutil.iter_modules(implementations.__path__)}


@pytest.fixture(scope="session")
def populator_help_pattern(populator_names):
    name_options = ",?|".join([imp.replace(".", "\\.") for imp in populator_names])
    return re.compile(f"{{({name_options},?)+}}")


def test_help():
    """Test that there are no errors when running a very basic command"""
    proc = run_cli("stac-populator", "--help")
    proc.check_returncode()


def test_run_implementation(populator_help_pattern, populator_names):
    """
    Test that all implementations can be loaded from the command line

    This test assumes that the pyessv-archive is installed in the default location.
    Run `make setup-pyessv-archive` prior to running this test.
    """
    proc = run_cli("stac-populator", "run", "--help")
    proc.check_returncode()
    populators = re.search(populator_help_pattern, proc.stdout)
    assert populator_names == set(populators.group(0).strip("{}").split(","))


def test_missing_implementation(populator_help_pattern, populator_names):
    """Test that implementations that can't load are missing from the options"""
    with tempfile.TemporaryDirectory() as dirname:
        pass  # this allows us to get a dirname that does not exist
    proc = run_cli("stac-populator", "run", "--help", env={**os.environ, "PYESSV_ARCHIVE_HOME": dirname})
    print(proc.stderr)
    proc.check_returncode()
    populators = re.search(populator_help_pattern, proc.stdout)
    assert "CMIP6_UofT" in populator_names  # sanity check
    assert "CMIP6_UofT" not in set(populators.group(0).strip("{}").split(","))


def test_export():
    proc = run_cli("stac-populator", "export", "--help")
    proc.check_returncode()
