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
./run.sh disk_usages --xnat_url https://xnat.health-ri.nl --report_path ./input_disk_usage_report.txt --study_overview ./studyoverview.csv
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
python src/xnat_maintenance_monitoring_scripts/users_per_project.py --xnat_url https://xnat.health-ri.nl
```
to query the whole XNAT.
Run the following to query only 'sandbox'
```bash
python src/xnat_maintenance_monitoring_scripts/users_per_project.py --xnat_url https://xnat.health-ri.nl --project sandbox
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
python src/xnat_maintenance_monitoring_scripts/disk_usages.py --xnat_url https://xnat.health-ri.nl --report_path ./input_disk_usage_report.txt --study_overview ./studyoverview.csv
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

### prearchive_cleanup.py

Removes XNAT prearchive uploads older than a configurable retention period, and verifies that each
deleted session is actually gone from disk. Uploads with no associated project ("unassigned") are
easy to forget about and can otherwise take up storage indefinitely.

Run in the terminal with:
```bash
python src/xnat_maintenance_monitoring_scripts/prearchive_cleanup.py \
  --xnat_url https://xnat.health-ri.nl \
  --project unassigned \
  --retention_days 90 \
  --project_root /data/xnat/prearchive
```
* `--project` accepts a specific project ID, `unassigned` (default) for uploads not associated with
  any project, or `all` to process every project including `unassigned`.
* `--retention_days` (default 90) is how old (in days, based on upload timestamp) a prearchive
  session must be before it's removed.
* `--project_root` must be a filesystem path to the XNAT prearchive directory, reachable from
  wherever the script runs, so it can confirm the session folder was actually removed from disk
  after the API delete.

`run.sh` alone isn't enough for this script, because it only mounts the current directory as
`/data` — `--project_root` needs the *real* prearchive directory. Run it via `docker run` directly
instead, mounting the prearchive directory read-only (the script only reads it to verify deletion;
the delete itself happens server-side via the XNAT API):
```bash
docker build -t xnat-scripts .
docker run --rm -it \
  -v /path/to/xnat/prearchive:/prearchive:ro \
  xnat-scripts prearchive_cleanup \
  --xnat_url https://xnat.health-ri.nl \
  --project unassigned \
  --retention_days 90 \
  --project_root /prearchive
```

#### Scheduled (cron) usage

Any script in this repository can be run on a recurring schedule *inside* the container, instead of
once per `docker run`. Start the container with `CRON_SCHEDULE` and `CRON_SCRIPT` set (and no
script name/args on the command line) and it will register a cron job and keep running:

```bash
docker build -t xnat-scripts .
docker run -d --name xnat-prearchive-cron \
  -v /path/to/xnat/prearchive:/prearchive:ro \
  -e CRON_SCHEDULE="0 3 * * *" \
  -e CRON_SCRIPT="prearchive_cleanup" \
  -e CRON_ARGS="--xnat_url https://xnat.health-ri.nl --project unassigned --retention_days 90 --project_root /prearchive" \
  -e XNAT_USERNAME="svc_cleanup" \
  -e XNAT_PASSWORD="********" \
  xnat-scripts

docker logs -f xnat-prearchive-cron
```
* `CRON_SCHEDULE` uses standard 5-field cron syntax (e.g. `"0 3 * * *"` = daily at 03:00).
* `CRON_SCRIPT` is any script name under `src/xnat_maintenance_monitoring_scripts/`, with or
  without `.py`.
* `CRON_ARGS` is the full CLI argument string for that script.
* `XNAT_USERNAME` / `XNAT_PASSWORD` let scripts that normally prompt interactively (like
  `prearchive_cleanup.py`) run unattended; they fall back to the interactive prompt when unset.
* Running `docker run ... xnat-scripts <script_name> [args]` (no `CRON_*` variables) continues to
  run the script once and exit, exactly as before — cron mode is purely additive.

### folder_cleanup.py

Removes files older than a configurable retention period from a given local directory (and any
now-empty parent directories left behind), independent of XNAT.

```bash
python src/xnat_maintenance_monitoring_scripts/folder_cleanup.py --dir_path /path/to/folder --retention_days 90
```

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

