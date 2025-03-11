import numpy as np


def test_np2py():
    """Test different use cases for np2py."""
    from STACpopulator.stac_utils import np2py

    # Test int
    i = np2py(np.int32(1))
    assert type(i) is int

    # Test float
    f = np2py(np.float32(1.0))
    assert type(f) is float

    # Test str
    s = np2py(np.str_("string"))
    assert type(s) is str

    # Test dict
    d = np2py({"a": np.int32(1), "b": np.float32(2.0)})
    assert d == {"a": 1, "b": 2.0}

    # Test list
    l_ = np2py([np.int32(1), np.float32(2.0)])
    assert l_ == [1, 2.0]

    # Test tuple
    t = np2py((np.int32(1), np.float32(2.0)))
    assert t == (1, 2.0)

    # Test NaNs
    n = np2py(np.float64(np.nan))
    assert type(n) is float

    # Test Infinity
    n = np2py(np.float64(np.inf))
    assert type(n) is float
