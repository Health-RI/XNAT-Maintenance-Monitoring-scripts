from unittest.mock import patch

from xnat_maintenance_monitoring_scripts import folder_cleanup


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
