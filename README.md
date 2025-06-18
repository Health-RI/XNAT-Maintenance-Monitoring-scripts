# XNAT Reporting Scripts

This repository contains Python scripts for generating reports from XNAT instances. The scripts can be run directly with Python or using the provided Docker setup.

## Docker Usage

### Prerequisites
- Docker installed on your system
- Input files placed in your current working directory

### Quick Start
1. Clone this repository
2. Navigate to the repository directory
3. Run scripts using the provided wrapper:

```bash
./run.sh <script_name> [script_arguments]
```

### Examples

Run users per project report:
```bash
./run.sh users_per_project --xnat_url https://xnat.health-ri.nl
```

Run users per project report for specific project:
```bash
./run.sh users_per_project --xnat_url https://xnat.health-ri.nl --project sandbox
```

Run disk usage report:
```bash
./run.sh disk_usages --xnat_url https://xnat.health-ri.nl --report_path ./output.txt --study_overview ./studyoverview.csv
```

The `run.sh` script will automatically:
- Build the Docker image
- Mount your current directory into the container
- Execute the specified script with your arguments
- Output files will be created in your current directory

## Direct Python Usage

You can also run the scripts directly with Python if you have the dependencies installed.

### users_per_project.py

Run in the terminal with:
```bash
python scripts/users_per_project.py --xnat_url https://xnat.health-ri.nl
```
to query the whole XNAT.
Run the following to query only 'sandbox'
```bash
python scripts/users_per_project.py --xnat_url https://xnat.health-ri.nl --project sandbox
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

### disk_usages.py

Run in the terminal with:
```bash
python scripts/disk_usages.py --xnat_url https://xnat.health-ri.nl --report_path ./output.txt --study_overview ./studyoverview.csv
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

## Contributing New Scripts

To add a new Python script to this repository:

1. Create your Python script following these guidelines:
   - Use argparse for command-line arguments
   - Include proper error handling
   - Write output files to the current working directory
   - Add dependencies to `requirements.txt` if needed

2. Place your `.py` file in the `scripts/` directory

3. The script will automatically be available in the Docker image after rebuilding

4. Update this README.md with documentation for your script

### Script Requirements
- Must be a standalone Python file (`.py` extension)
- Should handle authentication through user prompts (getpass)
- Input and output files should use the current working directory
- Follow the existing pattern of the current scripts

