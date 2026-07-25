"""Test-only dependency fallbacks for minimal offline environments."""
from __future__ import annotations

import sys
import types
from importlib.util import find_spec

if find_spec("requests") is None:
    requests_module = types.ModuleType("requests")
    adapters_module = types.ModuleType("requests.adapters")

    class HTTPAdapter:  # noqa: D101 - minimal test stub
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    class Session:  # noqa: D101 - minimal test stub
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def mount(self, *args: object, **kwargs: object) -> None:
            pass

        def get(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("requests is not installed in this test environment")

        def post(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("requests is not installed in this test environment")

        def close(self) -> None:
            pass

    adapters_module.HTTPAdapter = HTTPAdapter
    requests_module.Session = Session
    requests_module.adapters = adapters_module
    sys.modules["requests"] = requests_module
    sys.modules["requests.adapters"] = adapters_module

if find_spec("urllib3") is None:
    urllib3_module = types.ModuleType("urllib3")
    util_module = types.ModuleType("urllib3.util")
    retry_module = types.ModuleType("urllib3.util.retry")

    class Retry:  # noqa: D101 - minimal test stub
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    retry_module.Retry = Retry
    util_module.retry = retry_module
    urllib3_module.util = util_module
    sys.modules["urllib3"] = urllib3_module
    sys.modules["urllib3.util"] = util_module
    sys.modules["urllib3.util.retry"] = retry_module
