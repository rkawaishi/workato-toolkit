"""Sentinel guards for the service-integration skills:
/setup-workspace, /issue-api-keys, /deploy-project."""
from conftest import DOCS, SKILLS


def _read(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_setup_workspace_materializes_via_asset_tool():
    text = _read("setup-workspace")
    assert "workato_asset_path" in text
    for asset in ("workato-api.py", "ensure-workatoignore.sh", "workatoignore.template"):
        assert asset in text


def test_issue_api_keys_token_safety():
    text = _read("issue-api-keys")
    assert "Never print or echo the token" in text
    assert "--register-profile" in text
    assert "developer_api_clients" in text or "Developer API" in text
    # must disambiguate from the API Platform system
    assert "workato-api-systems" in text


def test_issue_api_keys_writes_org_record_only():
    text = _read("issue-api-keys")
    assert "org/docs/platform/developer-api-clients.md" in text


def test_issue_api_keys_reads_record_via_lookup():
    # READS go through the docs-overlay MCP (org record overlays the kit guide);
    # a direct file read of the org record as the read path is a regression.
    text = _read("issue-api-keys")
    assert 'workato_docs_lookup("platform/developer-api-clients.md")' in text
    assert "Read `org/docs/platform/developer-api-clients.md`" not in text


def test_deploy_project_reads_policy_via_lookup():
    text = _read("deploy-project")
    assert 'workato_docs_lookup("platform/developer-api-clients.md")' in text


def test_deploy_project_guards():
    text = _read("deploy-project")
    assert "Never approve a deployment" in text
    assert "dev" in text and "test" in text and "prod" in text
    assert "deploy preview" in text
    # promotion uses the helper's guarded commands, not raw push
    assert "workato push" not in text


def test_deploy_project_reads_environments_doc():
    text = _read("deploy-project")
    assert 'workato_docs_lookup("platform/environments.md")' in text


def test_kit_doc_for_developer_api_clients_exists():
    doc = DOCS / "platform" / "developer-api-clients.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    for token in ("api_privilege_group_id", "DEV", "TEST", "PROD", "all_folders"):
        assert token in text
