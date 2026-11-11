"""Generated agent docs must match the code.

`docs/agent-guide/code-map.md` and `docs/agent-guide/traceability.md` are written by
`.agent/tools/knowledge_map.py`. When a route, table, template, test or curated link
changes, run `make docs` and commit the result; these tests fail until you do.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".agent" / "tools" / "knowledge_map.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("knowledge_map", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_agent_docs_are_fresh(capsys) -> None:
    exit_code = load_tool().main(["--check"])
    report = capsys.readouterr().out
    assert exit_code == 0, (
        "docs/agent-guide is out of date. Run `make docs` and commit the result.\n" + report
    )


def test_code_map_lists_exactly_the_routes_the_app_serves(client: TestClient) -> None:
    """The map reads `app/main.py` statically; this proves it sees what FastAPI serves."""
    documented = {(route.method, route.path) for route in load_tool().build_model().routes}
    served = {
        (method, route.path)
        for route in client.app.routes
        if getattr(getattr(route, "endpoint", None), "__module__", "") == "app.main"
        for method in route.methods - {"HEAD", "OPTIONS"}
    }
    assert documented == served
