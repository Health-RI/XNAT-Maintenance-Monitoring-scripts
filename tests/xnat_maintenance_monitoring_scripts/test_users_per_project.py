import pandas as pd

from xnat_maintenance_monitoring_scripts import users_per_project


def test_sheet_name_sanitizes_and_truncates():
    used_names = set()

    assert users_per_project.sheet_name("Smith/Jones", used_names) == "Smith_Jones"
    assert len(users_per_project.sheet_name("x" * 40, used_names)) == 31


def test_sheet_name_empty_falls_back_to_no_pi():
    assert users_per_project.sheet_name("", set()) == users_per_project.NO_PI_SHEET_NAME


def test_sheet_name_deduplicates_case_insensitively():
    used_names = {"overview"}

    assert users_per_project.sheet_name("Overview", used_names) == "Overview (2)"
    assert users_per_project.sheet_name("overview", used_names) == "overview (3)"


def test_write_excel_overview_and_sheet_per_pi(tmp_path):
    df = pd.DataFrame(
        {
            "project": ["p1", "p2", "p3", "p4"],
            "pi_lastname": ["Smith", "Jones", "Smith", None],
        }
    )
    excel_path = tmp_path / "out.xlsx"

    users_per_project.write_excel(df, excel_path)

    sheets = pd.read_excel(excel_path, sheet_name=None)
    assert list(sheets) == ["Overview", "No PI", "Jones", "Smith"]
    assert len(sheets["Overview"]) == 4
    assert sheets["Smith"]["project"].tolist() == ["p1", "p3"]
    assert sheets["No PI"]["project"].tolist() == ["p4"]


def test_write_excel_empty_dataframe(tmp_path):
    excel_path = tmp_path / "out.xlsx"

    users_per_project.write_excel(pd.DataFrame(), excel_path)

    assert list(pd.read_excel(excel_path, sheet_name=None)) == ["Overview"]
