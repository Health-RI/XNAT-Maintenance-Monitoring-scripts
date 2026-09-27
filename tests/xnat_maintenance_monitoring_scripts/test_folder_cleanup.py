import errno
import os
import stat
from datetime import datetime, timedelta
from unittest.mock import patch

from xnat_maintenance_monitoring_scripts import folder_cleanup

RETENTION_DAYS = 90

def test_cleanup_path_does_not_exist(tmp_path, capsys):
    missing_path = tmp_path / "missing"

    folder_cleanup.cleanup(str(missing_path), RETENTION_DAYS)

    assert "path does not exist" in capsys.readouterr().out

def test_cleanup_path_not_a_directory(tmp_path, capsys):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    folder_cleanup.cleanup(str(file_path), RETENTION_DAYS)

    assert "path is not a directory" in capsys.readouterr().out
    assert file_path.exists()

@patch("os.path.islink")
def test_cleanup_path_is_symlink(mock_islink, tmp_path, capsys):
    mock_islink.return_value = True
    directory = tmp_path / "link_dir"
    directory.mkdir()

    folder_cleanup.cleanup(str(directory), RETENTION_DAYS)

    assert "path is a symbolic link" in capsys.readouterr().out
    assert directory.exists()

def test_cleanup_removes_old_file_but_keeps_fresh_empty_directory(tmp_path):
    directory = tmp_path / "dir"
    directory.mkdir()

    old_file = directory / "old.txt"
    old_file.write_text("old")
    _age(old_file, RETENTION_DAYS + 10)

    folder_cleanup.cleanup(str(directory), RETENTION_DAYS)

    assert not old_file.exists()
    assert directory.exists()

def test_cleanup_removes_empty_directory_once_it_ages_past_retention(tmp_path):
    directory = tmp_path / "aged_empty"
    directory.mkdir()
    _age(directory, RETENTION_DAYS + 10)

    folder_cleanup.cleanup(str(directory), RETENTION_DAYS)

    assert not directory.exists()

def test_cleanup_keeps_directory_with_fresh_file(tmp_path):
    directory = tmp_path / "dir"
    directory.mkdir()

    fresh_file = directory / "fresh.txt"
    fresh_file.write_text("fresh")
    _age(fresh_file, RETENTION_DAYS - 10)

    folder_cleanup.cleanup(str(directory), RETENTION_DAYS)

    assert fresh_file.exists()
    assert directory.exists()

def test_cleanup_recursively_removes_old_file_but_keeps_fresh_dirs(tmp_path, capsys):
    directory = tmp_path / "dir"

    subdir = directory / "subdir"
    subdir.mkdir(parents=True)

    old_file = subdir / "old.txt"
    old_file.write_text("old")
    _age(old_file, RETENTION_DAYS + 10)

    folder_cleanup.cleanup(str(directory), RETENTION_DAYS)
    out = capsys.readouterr().out

    assert not old_file.exists()
    assert subdir.exists()
    assert directory.exists()
    assert f"Successfully cleaned up directory {directory}" in out

def test_cleanup_removes_empty_subdir_once_it_ages_past_retention(tmp_path):
    directory = tmp_path / "dir"
    subdir = directory / "subdir"
    subdir.mkdir(parents=True)
    _age(subdir, RETENTION_DAYS + 10)

    folder_cleanup.cleanup(str(directory), RETENTION_DAYS)

    assert not subdir.exists()
    assert directory.exists()


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

@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_file_removal")
@patch("xnat_maintenance_monitoring_scripts.folder_cleanup.handle_directory")
@patch("os.path.isfile")
@patch("os.path.isdir")
@patch("os.path.islink")
def test_handle_path_symlink_is_ignored(mock_islink, mock_isdir, mock_isfile, mock_handle_directory, mock_handle_file_removal, capsys):
    mock_islink.return_value = True
    mock_isdir.return_value = True
    mock_isfile.return_value = False

    folder_cleanup.handle_path("some/symlink", 90)

    mock_handle_directory.assert_not_called()
    mock_handle_file_removal.assert_not_called()
    assert "symbolic link" in capsys.readouterr().out

def test_handle_directory_empty(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    _age(empty_dir, RETENTION_DAYS + 10)

    folder_cleanup.handle_directory(str(empty_dir), RETENTION_DAYS)

    assert not empty_dir.exists()

def test_handle_directory_empty_within_retention_kept(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    folder_cleanup.handle_directory(str(empty_dir), RETENTION_DAYS)

    assert empty_dir.exists()

def test_handle_directory_removes_old_file_but_keeps_fresh_empty_directory(tmp_path):
    directory = tmp_path / "all_old"
    directory.mkdir()
    old_file = directory / "old.txt"
    old_file.write_text("old")
    _age(old_file, RETENTION_DAYS + 10)

    folder_cleanup.handle_directory(str(directory), RETENTION_DAYS)

    assert not old_file.exists()
    assert directory.exists()

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

def test_handle_directory_recursively_removes_old_file_but_keeps_fresh_dirs(tmp_path):
    directory = tmp_path / "dir"
    subdir = directory / "subdir"
    subdir.mkdir(parents=True)
    old_file = subdir / "file.txt"
    old_file.write_text("old")
    _age(old_file, RETENTION_DAYS + 10)

    folder_cleanup.handle_directory(str(directory), RETENTION_DAYS)

    assert not old_file.exists()
    assert subdir.exists()
    assert directory.exists()

def test_handle_directory_removes_empty_subdir_once_it_ages_past_retention(tmp_path):
    directory = tmp_path / "dir"
    subdir = directory / "subdir"
    subdir.mkdir(parents=True)
    _age(subdir, RETENTION_DAYS + 10)

    folder_cleanup.handle_directory(str(directory), RETENTION_DAYS)

    assert not subdir.exists()
    assert directory.exists()

def test_handle_file_removal_exceeds_retention(tmp_path):
    file_path = tmp_path / "old.txt"
    file_path.write_text("old")
    _age(file_path, RETENTION_DAYS + 1)

    folder_cleanup.handle_file_removal(str(file_path), RETENTION_DAYS)

    assert not file_path.exists()

def test_handle_file_removal_within_retention(tmp_path):
    file_path = tmp_path / "fresh.txt"
    file_path.write_text("fresh")
    _age(file_path, RETENTION_DAYS - 10)

    folder_cleanup.handle_file_removal(str(file_path), RETENTION_DAYS)

    assert file_path.exists()

def test_handle_file_removal_at_retention_boundary(tmp_path):
    file_path = tmp_path / "boundary.txt"
    file_path.write_text("boundary")
    _age(file_path, RETENTION_DAYS)

    folder_cleanup.handle_file_removal(str(file_path), RETENTION_DAYS)

    assert file_path.exists()



@patch("os.remove")
def test_handle_file_removal_unrecoverable_error(mock_remove, tmp_path, capsys):
    mock_remove.side_effect = OSError("Permission denied by ACL")
    file_path = tmp_path / "locked.txt"
    file_path.write_text("content")
    _age(file_path, RETENTION_DAYS + 1)

    folder_cleanup.handle_file_removal(str(file_path), RETENTION_DAYS)

    assert file_path.exists()
    assert "Could not remove file" in capsys.readouterr().out



def _age(path, days_old):
    timestamp = (datetime.now() - timedelta(days=days_old)).timestamp()
    os.utime(path, (timestamp, timestamp))