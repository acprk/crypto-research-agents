import json
import os

import pytest

from cra_core.toolkit import init_project
from cra_mcp.install import BEGIN, HOSTS, doctor, install


@pytest.fixture
def proj(tmp_path):
    d = str(tmp_path / "p")
    init_project(d)
    return d


@pytest.mark.parametrize("host", HOSTS)
def test_every_host_installs_and_is_idempotent(proj, host, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))          # global configs must never be touched
    out1 = install(host, proj)
    out2 = install(host, proj)
    assert out1 and len(out1) == len(out2)
    assert not os.path.exists(tmp_path / "home")
    for root, _, files in os.walk(proj):
        for f in files:
            p = os.path.join(root, f)
            if f.endswith(".json") and ".cra" not in p:
                json.load(open(p))                                # valid JSON
            if f.endswith((".md", ".mdc")):
                assert open(p).read().count(BEGIN) <= 1           # guide block not duplicated


def test_merge_keeps_existing_servers(proj):
    with open(os.path.join(proj, ".mcp.json"), "w") as fh:
        json.dump({"mcpServers": {"other": {"command": "x"}}}, fh)
    install("claude-code", proj)
    cfg = json.load(open(os.path.join(proj, ".mcp.json")))
    assert set(cfg["mcpServers"]) == {"other", "cra"}
    assert cfg["mcpServers"]["cra"]["args"][:2] == ["-m", "cra_mcp.server"]


def test_vscode_uses_servers_key_and_opencode_uses_mcp_key(proj):
    install("vscode", proj)
    install("opencode", proj)
    assert "cra" in json.load(open(os.path.join(proj, ".vscode", "mcp.json")))["servers"]
    oc = json.load(open(os.path.join(proj, "opencode.json")))["mcp"]["cra"]
    assert oc["type"] == "local" and isinstance(oc["command"], list)


def test_dry_run_writes_nothing(proj):
    before = sorted(os.listdir(proj))
    install("cursor", proj, dry_run=True)
    assert sorted(os.listdir(proj)) == before


def test_doctor(proj, capsys):
    assert doctor(proj) == 0
    assert "core profile exposes 15 tools" in capsys.readouterr().out
