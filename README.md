# xnat-reporting-scripts
## users_per_project.py

Run in the terminal with:
```bash
python users_per_project.py --xnat_url https://xnat.health-ri.nl
```
to query the whole XNAT.
Run the following to query only 'sandbox'
```bash
python users_per_project.py --xnat_url https://xnat.health-ri.nl --project sandbox
```

You need to have 'Owner' or 'Site admin' priviliges to run this script on a project.
This script returns a CSV file "./{today}_XNAT_users_per_project.csv", with the columns:
* project
* user_login_name
* user_first_name
* user_last_name
* user_email
* access_level
* group
* pi_firstname
* pi_lastname
* pi_title
* pi_email
* pi_institution

## disk_usage.py

Run in the terminal with:
```bash
python script_name.py --xnat_url https://xnat.health-ri.nl --report_path ./output.txt --study_overview ./studyoverview.csv
```
to query the whole XNAT.

`report_path` is the `du` output from the server.
`study_overview` is a CSV file with a column 'main_study' and 'substudy' to link main studies to their substudies.

This script returns a CSV file "./{today}_XNAT_disk_usage.csv", with the columns:
* project_id
* main_study
* project_path
* data_usage (MB)
* xnat_project_name
* xnat_project_id
* pi_firstname
* pi_lastname
* pi_title
* pi_email
* pi_institution

