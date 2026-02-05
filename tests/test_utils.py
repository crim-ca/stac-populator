import os
import tempfile
from pathlib import Path

import pytest

from STACpopulator.exceptions import FunctionLoadError
from STACpopulator.utils import import_target


class TestImportTargetFromModule:
    """Test importing targets from installed modules."""

    def test_import_function_from_module(self):
        """Test importing a function from a module."""
        func = import_target("os.path:join")
        assert callable(func)
        assert func("a", "b") == os.path.join("a", "b")

    def test_import_class_from_module(self):
        """Test importing a class from a module."""
        cls = import_target("collections:OrderedDict")
        assert isinstance(cls, type)
        obj = cls([("a", 1), ("b", 2)])
        assert list(obj.keys()) == ["a", "b"]


class TestImportTargetFromFile:
    """Test importing targets from Python files"""

    def test_import_function_from_file(self):
        """Test importing a function from a Python file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "test_module.py"
            script_path.write_text("def test_func(x):\n    return x * 2\n")

            func = import_target(f"{script_path}:test_func")
            assert callable(func)
            assert func(5) == 10

    def test_import_class_from_file(self):
        """Test importing a class from a Python file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "test_module.py"
            script_path.write_text("class TestClass:\n    value = 42\n")

            cls = import_target(f"{script_path}:TestClass")
            assert isinstance(cls, type)
            assert cls.value == 42


class TestImportTargetErrors:
    """Test error handling in import_target"""

    def test_malformed_target_string(self):
        """Test that malformed target string raises FunctionLoadError"""
        with pytest.raises(FunctionLoadError, match="not properly formatted"):
            import_target("os.path")

    def test_missing_module(self):
        """Test that missing module raises FunctionLoadError"""
        with pytest.raises(FunctionLoadError, match="Unable to load module"):
            import_target("nonexistent_module:func")

    def test_missing_target_in_module(self):
        """Test that missing target in module raises FunctionLoadError"""
        with pytest.raises(FunctionLoadError, match="Unable to load target"):
            import_target("os:nonexistent_function")

    def test_missing_file(self):
        """Test that missing Python file raises FunctionLoadError"""
        with pytest.raises(FunctionLoadError, match="Unable to load python module from file"):
            import_target("/nonexistent/path/file.py:func")
