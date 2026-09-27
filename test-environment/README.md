# Test environment

A local XNAT 1.9.3.1 instance for testing the scripts in `src/`. Everything is
a docker compose service, so no manual setup steps are needed.

## Usage

```bash
docker compose up users_per_project
```

This brings up Postgres, XNAT and nginx, finishes XNAT's first-run setup, waits
for the REST API and loads the fixtures. It exits when the environment is
ready. First boot takes several minutes: the XNAT image is amd64, so it runs
under emulation on Apple Silicon.

Then run the script under test from the host:

```bash
python ../src/xnat_maintenance_monitoring_scripts/users_per_project.py \
    --xnat_url http://localhost:8080
```

with `admin` / `admin`. XNAT's web interface is on <http://localhost:8080>.

Tear down with `docker compose down -v && rm -rf data`.

## Services

| Service | Purpose |
|---|---|
| `xnat-db`, `xnat`, `nginx` | the XNAT instance itself |
| `xnat-setup` | first-run setup; exits once the REST API answers |
| `users_per_project` | loads `fixtures.yaml` for the users_per_project test |

`xnat-setup` is test-agnostic and reusable. A new test adds one service that
depends on it:

```yaml
  my_new_test:
    build: ./setup
    command: ["python", "populate.py"]
    environment:
      FIXTURES: /fixtures/my_fixtures.yaml
      # ... as for users_per_project
    volumes:
      - "./my_fixtures.yaml:/fixtures/my_fixtures.yaml:ro"
    depends_on:
      xnat-setup:
        condition: service_completed_successfully
```

Both `xnat-setup` and `populate.py` are idempotent, so re-running is safe.
`populate.py` only adds; it never removes users or roles dropped from the
fixtures.

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
the PI columns stay empty there. All accounts share one password
(`USER_PASSWORD`, default `TestPassword123!`).

XNAT rejects an empty `lastName`, so that case cannot be set up through the API.

## Notes

`setup/bootstrap.py` writes to the database directly. A fresh XNAT redirects
every request to the setup wizard and has no known admin password, so there is
no API-only way to get started. It also mounts the docker socket, to create the
data directories in the XNAT container and restart it. Throwaway local
instances only.

Two findings from running `users_per_project.py` against this environment are
recorded in `../SCRATCHPAD.md`; the disabled-user one means TESTPROJ02 and
TESTPROJ03 do not come out of the report the way the table above suggests.
