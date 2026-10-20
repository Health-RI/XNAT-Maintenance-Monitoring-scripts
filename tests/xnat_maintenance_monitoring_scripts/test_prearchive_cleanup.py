import argparse
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests
from xnat.exceptions import XNATResponseError

from xnat_maintenance_monitoring_scripts import prearchive_cleanup

RETENTION_DAYS = 90


def test_resolve_project_filter_all():
    assert prearchive_cleanup.resolve_project_filter("all") is None
    assert prearchive_cleanup.resolve_project_filter("ALL") is None


def test_resolve_project_filter_specific_project():
    assert prearchive_cleanup.resolve_project_filter("unassigned") == "unassigned"
    assert prearchive_cleanup.resolve_project_filter("my_project") == "my_project"


def test_delete_prearchive_session_via_api_success():
    prearchive_session = MagicMock()

    error = prearchive_cleanup.delete_prearchive_session_via_api(prearchive_session)

    prearchive_session.delete.assert_called_once_with(asynchronous=False)
    assert error is None


def test_delete_prearchive_session_via_api_failure():
    prearchive_session = MagicMock()
    prearchive_session.delete.side_effect = XNATResponseError("boom", MagicMock())

    error = prearchive_cleanup.delete_prearchive_session_via_api(prearchive_session)

    assert error == "boom"


def test_delete_prearchive_session_via_api_connection_failure():
    prearchive_session = MagicMock()
    prearchive_session.delete.side_effect = requests.exceptions.ConnectionError("unreachable")

    error = prearchive_cleanup.delete_prearchive_session_via_api(prearchive_session)

    assert error == "unreachable"


def test_delete_prearchive_session_via_api_unexpected_error_propagates():
    prearchive_session = MagicMock()
    prearchive_session.delete.side_effect = TypeError("bug")

    with pytest.raises(TypeError):
        prearchive_cleanup.delete_prearchive_session_via_api(prearchive_session)


def test_non_negative_int_accepts_zero_and_positive():
    assert prearchive_cleanup.non_negative_int("0") == 0
    assert prearchive_cleanup.non_negative_int("1") == 1


def test_non_negative_int_rejects_negative():
    with pytest.raises(argparse.ArgumentTypeError):
        prearchive_cleanup.non_negative_int("-1")


def test_is_disk_path_deleted_when_present(tmp_path):
    disk_path = tmp_path / "session_folder"
    disk_path.mkdir()

    assert prearchive_cleanup.is_disk_path_deleted(disk_path) is False


def test_is_disk_path_deleted_when_absent(tmp_path):
    disk_path = tmp_path / "session_folder"

    assert prearchive_cleanup.is_disk_path_deleted(disk_path) is True


def make_prearchive_session():
    prearchive_session = MagicMock()
    prearchive_session.project = "my_project"
    prearchive_session.data = {"timestamp": "20260101_120000"}
    prearchive_session.label = "SESSION_1"
    setattr(prearchive_session, prearchive_cleanup.PREARCHIVE_FOLDER_FIELD, "SESSION_1_folder")
    return prearchive_session


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.is_disk_path_deleted")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session_via_api")
def test_delete_prearchive_session_api_error_skips_disk_check(mock_delete_via_api, mock_is_disk_path_deleted):
    mock_delete_via_api.return_value = "boom"
    prearchive_session = make_prearchive_session()

    result = prearchive_cleanup.delete_prearchive_session(prearchive_session, "/prearchive_root")

    mock_is_disk_path_deleted.assert_not_called()
    assert result == {"deleted": False, "disk_verified": None, "error": "boom"}


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.is_disk_path_deleted")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session_via_api")
def test_delete_prearchive_session_verified(mock_delete_via_api, mock_is_disk_path_deleted):
    mock_delete_via_api.return_value = None
    mock_is_disk_path_deleted.return_value = True
    prearchive_session = make_prearchive_session()

    result = prearchive_cleanup.delete_prearchive_session(prearchive_session, "/prearchive_root")

    assert result == {"deleted": True, "disk_verified": True, "error": None}


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.is_disk_path_deleted")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session_via_api")
def test_delete_prearchive_session_not_verified(mock_delete_via_api, mock_is_disk_path_deleted):
    mock_delete_via_api.return_value = None
    mock_is_disk_path_deleted.return_value = False
    prearchive_session = make_prearchive_session()

    result = prearchive_cleanup.delete_prearchive_session(prearchive_session, "/prearchive_root")

    assert result == {"deleted": True, "disk_verified": False, "error": None}


def test_list_prearchive_sessions_passes_through_project_filter():
    xnat_session = MagicMock()
    xnat_session.prearchive.sessions.return_value = ["session_1"]

    result = prearchive_cleanup.list_prearchive_sessions(xnat_session, "my_project")

    xnat_session.prearchive.sessions.assert_called_once_with(project="my_project")
    assert result == ["session_1"]


def test_is_expired_true_past_retention():
    now = datetime(2026, 1, 1)
    timestamp = now - timedelta(days=RETENTION_DAYS + 1)

    assert prearchive_cleanup.is_expired(timestamp, RETENTION_DAYS, now) is True


def test_is_expired_false_at_boundary():
    now = datetime(2026, 1, 1)
    timestamp = now - timedelta(days=RETENTION_DAYS)

    assert prearchive_cleanup.is_expired(timestamp, RETENTION_DAYS, now) is False


def test_is_expired_false_within_retention():
    now = datetime(2026, 1, 1)
    timestamp = now - timedelta(days=RETENTION_DAYS - 1)

    assert prearchive_cleanup.is_expired(timestamp, RETENTION_DAYS, now) is False


def test_filter_expired_sessions_returns_only_expired():
    now = datetime(2026, 1, 1)
    expired_session = MagicMock(timestamp=now - timedelta(days=RETENTION_DAYS + 1))
    fresh_session = MagicMock(timestamp=now - timedelta(days=1))

    result = prearchive_cleanup.filter_expired_sessions([expired_session, fresh_session], RETENTION_DAYS, now)

    assert result == [expired_session]


def test_build_prearchive_disk_path():
    result = prearchive_cleanup.build_prearchive_disk_path(
        "/prearchive_root", "my_project", "20260101_120000", "SESSION_1_folder"
    )

    assert str(result) == str(prearchive_cleanup.Path("/prearchive_root/my_project/20260101_120000/SESSION_1_folder"))


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.list_prearchive_sessions")
def test_cleanup_prearchive_resolves_all_to_none_filter(mock_list_sessions, mock_delete_session):
    mock_list_sessions.return_value = []

    prearchive_cleanup.cleanup_prearchive(MagicMock(), "all", RETENTION_DAYS, "/prearchive_root")

    assert mock_list_sessions.call_args.args[1] is None


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.list_prearchive_sessions")
def test_cleanup_prearchive_counts_and_aggregates(mock_list_sessions, mock_delete_session):
    now = datetime.now()
    expired_session = MagicMock(timestamp=now - timedelta(days=RETENTION_DAYS + 1))
    mock_list_sessions.return_value = [expired_session]
    mock_delete_session.return_value = {"deleted": True, "disk_verified": True, "error": None}

    result = prearchive_cleanup.cleanup_prearchive(MagicMock(), "unassigned", RETENTION_DAYS, "/prearchive_root")

    mock_delete_session.assert_called_once_with(expired_session, "/prearchive_root")
    assert result == {"checked": 1, "deleted": 1, "disk_warnings": 0, "errors": 0}


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.list_prearchive_sessions")
def test_cleanup_prearchive_counts_disk_warning(mock_list_sessions, mock_delete_session):
    now = datetime.now()
    expired_session = MagicMock(timestamp=now - timedelta(days=RETENTION_DAYS + 1))
    mock_list_sessions.return_value = [expired_session]
    mock_delete_session.return_value = {"deleted": True, "disk_verified": False, "error": None}

    result = prearchive_cleanup.cleanup_prearchive(MagicMock(), "unassigned", RETENTION_DAYS, "/prearchive_root")

    assert result == {"checked": 1, "deleted": 1, "disk_warnings": 1, "errors": 0}


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.list_prearchive_sessions")
def test_cleanup_prearchive_counts_error(mock_list_sessions, mock_delete_session):
    now = datetime.now()
    expired_session = MagicMock(timestamp=now - timedelta(days=RETENTION_DAYS + 1))
    mock_list_sessions.return_value = [expired_session]
    mock_delete_session.return_value = {"deleted": False, "disk_verified": None, "error": "boom"}

    result = prearchive_cleanup.cleanup_prearchive(MagicMock(), "unassigned", RETENTION_DAYS, "/prearchive_root")

    assert result == {"checked": 1, "deleted": 0, "disk_warnings": 0, "errors": 1}


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.delete_prearchive_session")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.list_prearchive_sessions")
def test_cleanup_prearchive_empty_sessions(mock_list_sessions, mock_delete_session):
    mock_list_sessions.return_value = []

    result = prearchive_cleanup.cleanup_prearchive(MagicMock(), "unassigned", RETENTION_DAYS, "/prearchive_root")

    mock_delete_session.assert_not_called()
    assert result == {"checked": 0, "deleted": 0, "disk_warnings": 0, "errors": 0}


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.cleanup_prearchive")
@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.xnat.connect")
def test_main_connects_and_delegates_to_cleanup(mock_connect, mock_cleanup_prearchive):
    session = MagicMock()
    mock_connect.return_value.__enter__.return_value = session

    prearchive_cleanup.main("https://xnat.example.org", "user", "pass", "unassigned", RETENTION_DAYS, "/prearchive_root")

    mock_connect.assert_called_once_with("https://xnat.example.org", user="user", password="pass")
    mock_cleanup_prearchive.assert_called_once_with(session, "unassigned", RETENTION_DAYS, "/prearchive_root")


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.getpass.getpass")
@patch("builtins.input")
def test_resolve_credentials_uses_env_vars_when_present(mock_input, mock_getpass):
    with patch.dict(os.environ, {"XNAT_USERNAME": "env_user", "XNAT_PASSWORD": "env_pass"}, clear=True):
        username, password = prearchive_cleanup.resolve_credentials()

    assert (username, password) == ("env_user", "env_pass")
    mock_input.assert_not_called()
    mock_getpass.assert_not_called()


@patch("xnat_maintenance_monitoring_scripts.prearchive_cleanup.getpass.getpass")
@patch("builtins.input")
def test_resolve_credentials_falls_back_to_prompts_when_env_absent(mock_input, mock_getpass):
    mock_input.return_value = "prompted_user"
    mock_getpass.return_value = "prompted_pass"

    with patch.dict(os.environ, {}, clear=True):
        username, password = prearchive_cleanup.resolve_credentials()

    assert (username, password) == ("prompted_user", "prompted_pass")
    mock_input.assert_called_once()
    mock_getpass.assert_called_once()
