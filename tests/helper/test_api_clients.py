#!/usr/bin/env python3
"""Tests for the api-clients command group (Developer API clients).

Covers:
  - argparse surface: subcommands exist; create requires name/environment/role-id
  - mutations refuse to run without an explicit --profile
  - --dry-run prints the intended request and never calls the API
  - the issued token is never written to stdout/stderr
  - register_profile stores token via keyring and updates ~/.workato/profiles
  - rotate is delete + same-name create and requires --yes

Run with:
    python3 -m pytest tests/helper/test_api_clients.py -q
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parents[1] / "plugin" / "scripts" / "workato-api.py"

spec = importlib.util.spec_from_file_location("workato_api", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["workato_api"] = mod
spec.loader.exec_module(mod)

SECRET = "tok-SECRET-abc123"


class FakeAPI(mod.WorkatoAPI):
    """Real WorkatoAPI methods over a canned _request; records calls."""

    def __init__(self):
        self.base_url = "https://app.example.com"
        self.token = "admin-token"
        self.calls = []

    def _request(self, path, params=None, method="GET", body=None):
        self.calls.append((method, path, body))
        if method == "POST" and path == "/api/developer_api_clients":
            return {"result": {"id": 77, "name": body["name"],
                               "environment": body.get("environment"),
                               "token": {"value": SECRET}}}
        if method == "GET" and path == "/api/developer_api_clients":
            return {"result": [{"id": 77, "name": "acme-agent-dev",
                                "environment": "DEV",
                                "api_privilege_group_id": 547,
                                "all_folders": True}]}
        if method == "DELETE" and path.startswith("/api/developer_api_clients/"):
            return {"result": "success"}
        if path == "/api/users/me":
            return {"id": 4242, "name": "svc"}
        return {}


def _args(**kw):
    base = dict(profile="acme-admin", dry_run=False, yes=False,
                name=None, environment=None, role_id=None,
                all_folders=True, folder_ids=None, ip_allow_list=None,
                register_profile=None, region=None, client_id=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_parser_has_api_clients_subcommands():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "api-clients", "--help"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0
    for sub in ("list", "roles", "create", "delete", "rotate"):
        assert sub in out.stdout


def test_create_requires_name_environment_role():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "api-clients", "create"],
        capture_output=True, text=True,
    )
    assert out.returncode == 2  # argparse: missing required arguments
    for req in ("--name", "--environment", "--role-id"):
        assert req in out.stderr


def test_create_dry_run_prints_request_and_skips_api():
    api = FakeAPI()
    out = io.StringIO()
    with redirect_stdout(out):
        mod.cmd_api_clients_create(api, _args(
            name="acme-agent-dev", environment="DEV", role_id=547, dry_run=True))
    assert api.calls == [], "dry-run must not call the API"
    text = out.getvalue()
    assert "acme-agent-dev" in text and "DEV" in text and "547" in text


def test_create_never_prints_token(monkeypatch):
    monkeypatch.setattr(mod, "register_profile",
                        lambda *a, **k: ("keyring", "acme-dev"))
    api = FakeAPI()
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        mod.cmd_api_clients_create(api, _args(
            name="acme-agent-dev", environment="DEV", role_id=547,
            register_profile="acme-dev"))
    assert SECRET not in out.getvalue()
    assert SECRET not in err.getvalue()
    assert "77" in out.getvalue()  # client id is reported


def test_mutation_requires_explicit_profile():
    api = FakeAPI()
    try:
        mod.cmd_api_clients_create(api, _args(
            profile=None, name="x", environment="DEV", role_id=1))
        raised = False
    except SystemExit as e:
        raised = e.code != 0
    assert raised, "create without --profile must exit non-zero"
    assert api.calls == []


def test_delete_requires_yes():
    api = FakeAPI()
    try:
        mod.cmd_api_clients_delete(api, _args(client_id=77, yes=False))
        raised = False
    except SystemExit as e:
        raised = e.code != 0
    assert raised
    assert api.calls == []


def test_rotate_is_delete_then_same_name_create():
    api = FakeAPI()
    out = io.StringIO()
    with redirect_stdout(out):
        mod.cmd_api_clients_rotate(api, _args(name="acme-agent-dev", yes=True))
    methods = [(m, p) for m, p, _ in api.calls]
    assert ("DELETE", "/api/developer_api_clients/77") in methods
    posts = [b for m, p, b in api.calls if m == "POST"]
    assert posts and posts[0]["name"] == "acme-agent-dev"
    assert posts[0]["environment"] == "DEV"
    assert SECRET not in out.getvalue()


def _profiles_file(tmp_path, monkeypatch):
    profiles = tmp_path / "profiles"
    profiles.write_text(json.dumps({
        "current_profile": "acme-admin",
        "profiles": {"acme-admin": {"region": "jp",
                                    "region_url": "https://app.jp.workato.com",
                                    "workspace_id": 1}}}), encoding="utf-8")
    monkeypatch.setattr(mod, "PROFILES_PATH", profiles)
    return profiles


class _StubUsersMeAPI:
    def __init__(self, base_url, token):
        pass

    def users_me(self):
        return {"id": 4242, "name": "svc"}


def test_register_profile_rejects_unknown_source_profile(tmp_path, monkeypatch):
    profiles = _profiles_file(tmp_path, monkeypatch)
    before = profiles.read_text()
    try:
        mod.register_profile(FakeAPI(), profile_name="acme-dev", token=SECRET,
                             source_profile="nope-admin")
        raised = False
    except SystemExit as e:
        raised = e.code != 0
    assert raised, "unknown source profile must exit non-zero"
    assert profiles.read_text() == before, "profiles must not be touched"


def test_register_profile_users_me_failure_leaves_profiles_untouched(tmp_path, monkeypatch):
    profiles = _profiles_file(tmp_path, monkeypatch)
    before = profiles.read_text()

    class BoomAPI:
        def __init__(self, base_url, token):
            pass

        def users_me(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(mod, "WorkatoAPI", BoomAPI)
    try:
        mod.register_profile(FakeAPI(), profile_name="acme-dev", token=SECRET,
                             source_profile="acme-admin")
        raised = False
    except RuntimeError:
        raised = True
    assert raised
    assert profiles.read_text() == before


def test_register_profile_fallback_file_is_0600_in_0700_dir_and_silent(tmp_path, monkeypatch):
    profiles = _profiles_file(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "WorkatoAPI", _StubUsersMeAPI)
    monkeypatch.setitem(sys.modules, "keyring", None)  # import keyring -> ImportError
    monkeypatch.setattr(mod, "PENDING_TOKENS_DIR", tmp_path / "pending")
    out = io.StringIO()
    with redirect_stdout(out):
        method, where = mod.register_profile(
            FakeAPI(), profile_name="acme-dev", token=SECRET,
            source_profile="acme-admin")
    assert method == "file"
    tf = Path(where)
    assert tf.read_text(encoding="utf-8") == SECRET
    assert (tf.stat().st_mode & 0o777) == 0o600, "token file must be 0600 from birth"
    assert (tf.parent.stat().st_mode & 0o777) == 0o700, "pending dir must be 0700"
    text = out.getvalue()
    assert SECRET not in text
    assert "$(cat" not in text, "guidance must not expand the token into argv"
    # profiles updated only after the token was stored
    data = json.loads(profiles.read_text())
    assert data["profiles"]["acme-dev"]["workspace_id"] == 4242


def test_register_profile_no_profiles_write_when_all_storage_fails(tmp_path, monkeypatch):
    profiles = _profiles_file(tmp_path, monkeypatch)
    before = profiles.read_text()
    monkeypatch.setattr(mod, "WorkatoAPI", _StubUsersMeAPI)
    monkeypatch.setitem(sys.modules, "keyring", None)

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(mod, "_store_token_fallback", boom)
    try:
        mod.register_profile(FakeAPI(), profile_name="acme-dev", token=SECRET,
                             source_profile="acme-admin")
        raised = False
    except OSError:
        raised = True
    assert raised
    assert profiles.read_text() == before, \
        "profiles must not point at a profile whose token was never stored"


def test_create_without_register_writes_0600_pending_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "PENDING_TOKENS_DIR", tmp_path / "pending")
    api = FakeAPI()
    out = io.StringIO()
    with redirect_stdout(out):
        mod.cmd_api_clients_create(api, _args(
            name="acme-agent-dev", environment="DEV", role_id=547))
    tf = tmp_path / "pending" / "client-77.token"
    assert tf.read_text(encoding="utf-8") == SECRET
    assert (tf.stat().st_mode & 0o777) == 0o600
    assert (tf.parent.stat().st_mode & 0o777) == 0o700
    assert SECRET not in out.getvalue()


def test_register_profile_uses_keyring_and_profiles_file(tmp_path, monkeypatch):
    stored = {}

    class FakeKeyring:
        @staticmethod
        def set_password(service, name, value):
            stored[(service, name)] = value

    class StubAPI:
        def __init__(self, base_url, token):
            assert token == SECRET

        def users_me(self):
            return {"id": 4242, "name": "svc"}

    monkeypatch.setitem(sys.modules, "keyring", FakeKeyring)
    monkeypatch.setattr(mod, "WorkatoAPI", StubAPI)
    profiles = tmp_path / "profiles"
    profiles.write_text(json.dumps({
        "current_profile": "acme-admin",
        "profiles": {"acme-admin": {"region": "jp",
                                    "region_url": "https://app.jp.workato.com",
                                    "workspace_id": 1}}}), encoding="utf-8")
    monkeypatch.setattr(mod, "PROFILES_PATH", profiles)
    api = FakeAPI()
    method, name = mod.register_profile(
        api, profile_name="acme-dev", token=SECRET, source_profile="acme-admin")
    assert method == "keyring" and name == "acme-dev"
    assert stored[("workato-platform-cli", "acme-dev")] == SECRET
    data = json.loads(profiles.read_text())
    assert data["profiles"]["acme-dev"]["workspace_id"] == 4242
    assert data["profiles"]["acme-dev"]["region"] == "jp"
