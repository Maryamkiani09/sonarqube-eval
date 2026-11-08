"""LIVE tests - Person 6: Web API, plugins, localization, database, automation."""
import re
import uuid

import pytest

from sonar_tools import admin, system

pytestmark = pytest.mark.integration


def test_p6_01_server_version_format(live):
    assert re.match(r"^\d+\.\d+", system.server_version(live))


def test_p6_02_database_engine_reported(live):
    info = system.database_info(live)
    assert info["vendor"] in {"PostgreSQL", "H2", "Oracle", "Microsoft SQL Server"}, info
    print(f"\n[finding] database: {info}")


def test_p6_03_installed_plugins_include_python_analyzer(live):
    keys = {p["key"] for p in system.installed_plugins(live)}
    assert "python" in keys


def test_p6_04_marketplace_call_is_safe(live):
    assert isinstance(system.available_plugins(live), list)


def test_p6_05_localization_packs_are_plugins(live):
    packs = [p["key"] for p in system.installed_plugins(live) if p["key"].startswith("l10n")]
    if not packs:
        pytest.skip("only the built-in English pack is installed (install a l10n plugin to test UI languages)")
    assert all(k.startswith("l10n") for k in packs)


def test_p6_06_supported_languages_listed(live):
    keys = {lang["key"] for lang in system.supported_languages(live)}
    assert {"py", "java", "js"} <= keys


def test_p6_07_user_group_permission_automation(live, project_key):
    suffix = uuid.uuid4().hex[:6]
    login, group = f"eval-{suffix}", f"eval-grp-{suffix}"
    try:
        admin.create_user(live, login, "Eval User", "Passw0rd!" + suffix)
        admin.create_group(live, group)
        admin.add_user_to_group(live, group, login)
        admin.grant_permission(live, "codeviewer", project=project_key, group=group)
    finally:
        admin.deactivate_user(live, login)
        live.post("api/user_groups/delete", name=group)


def test_p6_08_settings_roundtrip(live, project_key):
    admin.set_exclusions(live, project_key, ["**/generated/**"])
    try:
        assert admin.get_setting(live, "sonar.exclusions", project_key)["values"] == ["**/generated/**"]
    finally:
        admin.reset_setting(live, "sonar.exclusions", project_key)
