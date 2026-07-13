import os
from datetime import datetime, timedelta
from unittest.mock import patch

from xnat_maintenance_monitoring_scripts import folder_cleanup

RETENTION_DAYS = 90

@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_file_removal")
@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_directory")
@patch("os.path.isfile")
@patch("os.path.isdir")
def test_handle_path_dir(mock_isdir, mock_isfile, mock_handle_directory, mock_handle_file_removal):
    mock_isdir.return_value = True
    mock_isfile.return_value = False

    folder_cleanup.handle_path("some/dir", 90)

    mock_handle_directory.assert_called_once_with("some/dir", 90)
    mock_handle_file_removal.assert_not_called()


@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_file_removal")
@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_directory")
@patch("os.path.isfile")
@patch("os.path.isdir")
def test_handle_path_file(mock_isdir, mock_isfile, mock_handle_directory, mock_handle_file_removal):
    mock_isdir.return_value = False
    mock_isfile.return_value = True

    folder_cleanup.handle_path("some/file.txt", 90)

    mock_handle_file_removal.assert_called_once_with("some/file.txt", 90)
    mock_handle_directory.assert_not_called()


@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_file_removal")
@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_directory")
@patch("os.path.isfile")
@patch("os.path.isdir")
def test_handle_path_neither_file_nor_dir(mock_isdir, mock_isfile, mock_handle_directory, mock_handle_file_removal):
    mock_isdir.return_value = False
    mock_isfile.return_value = False

    folder_cleanup.handle_path("broken/symlink", 90)

    mock_handle_directory.assert_not_called()
    mock_handle_file_removal.assert_not_called()

def test_handle_directory_empty(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    folder_cleanup.handle_directory(str(empty_dir), RETENTION_DAYS)

    assert not empty_dir.exists()


def test_handle_directory_not_empty_all_exceed_retention(tmp_path):
    directory = tmp_path / "all_old"
    directory.mkdir()
    old_file = directory / "old.txt"
    old_file.write_text("old")
    _age(old_file, RETENTION_DAYS + 10)

    folder_cleanup.handle_directory(str(directory), RETENTION_DAYS)

    assert not old_file.exists()
    assert not directory.exists()


def test_handle_directory_not_empty_all_within_retention(tmp_path):
    directory = tmp_path / "all_fresh"
    directory.mkdir()
    fresh_file = directory / "fresh.txt"
    fresh_file.write_text("fresh")
    _age(fresh_file, RETENTION_DAYS - 10)

    folder_cleanup.handle_directory(str(directory), RETENTION_DAYS)

    assert fresh_file.exists()
    assert directory.exists()


def test_handle_directory_mixed_contents(tmp_path):
    directory = tmp_path / "mixed"
    directory.mkdir()
    old_file = directory / "old.txt"
    fresh_file = directory / "fresh.txt"
    old_file.write_text("old")
    fresh_file.write_text("fresh")
    _age(old_file, RETENTION_DAYS + 10)
    _age(fresh_file, RETENTION_DAYS - 10)

    folder_cleanup.handle_directory(str(directory), RETENTION_DAYS)

    assert not old_file.exists()
    assert fresh_file.exists()
    assert directory.exists()


def test_handle_directory_nested_recursive_cleanup(tmp_path):
    directory = tmp_path / "dir"
    subdir = directory / "subdir"
    subdir.mkdir(parents=True)
    old_file = subdir / "file.txt"
    old_file.write_text("old")
    _age(old_file, RETENTION_DAYS + 10)

    folder_cleanup.handle_directory(str(directory), RETENTION_DAYS)

    assert not old_file.exists()
    assert not subdir.exists()
    assert not directory.exists()

def _age(path, days_old):
    timestamp = (datetime.now() - timedelta(days=days_old)).timestamp()
    os.utime(path, (timestamp, timestamp))