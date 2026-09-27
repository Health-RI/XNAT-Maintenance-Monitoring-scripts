# Test environment

A local XNAT 1.9.3.1 instance, populated with five projects and ten users, for
testing `users_per_project.py`.

## Usage

```bash
pip install -r requirements.txt

docker compose up -d          # first boot takes a few minutes
python bootstrap.py           # set admin password, finish site setup, restart
python populate.py            # create the users and projects
```

Wait for the REST API before populating:

```bash
until curl -sf -u admin:admin http://localhost:8080/data/projects?format=json >/dev/null; do sleep 10; done
```

XNAT is then on <http://localhost:8080> with admin/admin, and the script can be
run against it:

```bash
python ../src/xnat_maintenance_monitoring_scripts/users_per_project.py \
    --xnat_url http://localhost:8080
```

Tear down with `docker compose down -v && rm -rf data`.

`populate.py` is idempotent, so it can be re-run after editing `fixtures.yaml`.
Note that it only adds; it never removes users or roles that are no longer in
the fixtures.

## What gets created

Defined in `fixtures.yaml`.

| Project | Users | Covers |
|---|---|---|
| TESTPROJ01 Cardiac Imaging Study | a.owner, b.member, c.collab | one of each access level |
| TESTPROJ02 Neuro Longitudinal | g.admin, d.disabled, e.unverified, f.multi | disabled and unverified accounts |
| TESTPROJ03 Oncology Pilot | h.disabled.owner, b.member | the only owner is disabled |
| TESTPROJ04 Musculoskeletal Cohort | j.accented, i.longname, f.multi | non-ASCII and multi-part surnames |
| TESTPROJ05 Empty Study | a.owner | no PI metadata, single user |

`f.multi` and `b.member` sit in several projects, and TESTPROJ05 has no PI, so
the PI columns stay empty there. All accounts get the same password
(`--user_password`, default `TestPassword123!`).

XNAT rejects an empty `lastName`, so that case cannot be set up through the API.

## Notes

`bootstrap.py` writes to the database directly. A fresh XNAT redirects every
request to the setup wizard and has no known admin password, so there is no
API-only way to get started. It is meant for a throwaway local instance only.

The image is amd64, so it runs under emulation on Apple Silicon and is slow to
boot.

Two findings from running `users_per_project.py` against this environment are
recorded in `../SCRATCHPAD.md`; the disabled-user one means TESTPROJ02 and
TESTPROJ03 do not come out of the report the way the table above suggests.
