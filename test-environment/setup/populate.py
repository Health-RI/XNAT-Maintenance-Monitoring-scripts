"""Populate an XNAT test instance with projects and users.

Reads a declarative fixture file (fixtures.yaml) and creates the described
users and projects on the target XNAT, assigning per-project access levels
and toggling the enabled/verified flags. Safe to re-run: existing users and
projects are reused rather than recreated.

Runs as the `populate` compose service; configured through environment
variables so it needs no interactive input.
"""

from __future__ import annotations

import os
import sys
from typing import Any
from xml.sax.saxutils import escape

import xnat
import yaml

# XNAT's project user groups.
ACCESS_LEVELS = ("owner", "member", "collaborator")

PROJECT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<xnat:Project ID="{id}" xmlns:xnat="http://nrg.wustl.edu/xnat"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <xnat:name>{name}</xnat:name>
  <xnat:description>{description}</xnat:description>
{pi}</xnat:Project>
"""

PI_XML = """  <xnat:PI>
    <xnat:firstname>{pi_firstname}</xnat:firstname>
    <xnat:lastname>{pi_lastname}</xnat:lastname>
    <xnat:title>{pi_title}</xnat:title>
    <xnat:institution>{pi_institution}</xnat:institution>
  </xnat:PI>
"""


def load_fixtures(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def existing_logins(session) -> list[str]:
    """Return all login names known to the server.

    Uses /xapi/users rather than session.users: the latter is backed by
    /data/users, which omits disabled accounts and would make this script
    try to re-create them.
    """
    return session.get_json("/xapi/users")


def create_user(session, spec: dict[str, Any], password: str, existing: list[str]) -> None:
    """Create a user, then apply its enabled/verified flags."""
    login = spec["login"]

    if login in existing:
        print(f"  user {login} already exists, updating flags only")
    else:
        payload = {
            "username": login,
            "firstName": spec["first_name"],
            "lastName": spec["last_name"],
            "email": spec["email"],
            "password": password,
            "admin": spec.get("admin", False),
            # Create every account active; the flags are applied below so that
            # the same code path runs on a re-run against existing users.
            "enabled": True,
            "verified": True,
        }
        session.post("/xapi/users", json=payload, accepted_status=[200, 201])
        print(f"  created user {login}")

    # Applied separately: XNAT ignores these fields on the creation payload.
    for flag in ("enabled", "verified"):
        value = spec.get(flag, True)
        session.put(
            f"/xapi/users/{login}/{flag}/{str(value).lower()}",
            accepted_status=[200, 201, 204],
        )
    print(f"    enabled={spec.get('enabled', True)} verified={spec.get('verified', True)}")


def build_project_xml(spec: dict[str, Any]) -> str:
    pi = ""
    if spec.get("pi_lastname"):
        pi = PI_XML.format(
            pi_firstname=escape(spec.get("pi_firstname", "")),
            pi_lastname=escape(spec.get("pi_lastname", "")),
            pi_title=escape(spec.get("pi_title", "")),
            pi_institution=escape(spec.get("pi_institution", "")),
        )
    return PROJECT_XML.format(
        id=escape(spec["id"]),
        name=escape(spec["name"]),
        description=escape(spec.get("description", "")),
        pi=pi,
    )


def create_project(session, spec: dict[str, Any]) -> None:
    project_id = spec["id"]

    if project_id in session.projects:
        print(f"  project {project_id} already exists, reusing")
    else:
        session.post(
            "/data/archive/projects",
            data=build_project_xml(spec).encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            accepted_status=[200, 201],
        )
        # The projects listing is cached, so a freshly created project is not
        # visible until the cache is dropped.
        session.clearcache()
        print(f"  created project {project_id}")

    project = session.projects[project_id]
    for login, level in spec.get("members", {}).items():
        if level not in ACCESS_LEVELS:
            raise ValueError(f"{project_id}/{login}: unknown access level {level!r}, expected one of {ACCESS_LEVELS}")
        project.set_access(login, level)
        print(f"    {login} -> {level}")


def main(xnat_url: str, username: str, password: str, fixtures_path: str, user_password: str) -> None:
    fixtures = load_fixtures(fixtures_path)

    with xnat.connect(xnat_url, user=username, password=password) as session:
        print(f"Connected to {xnat_url}")

        existing = existing_logins(session)

        failures = []

        print("Users:")
        for user_spec in fixtures.get("users", []):
            try:
                create_user(session, user_spec, user_password, existing)
            # Broad on purpose: one bad fixture should not stop the rest.
            except Exception as error:  # NOSONAR
                failures.append(f"user {user_spec['login']}: {error}")
                print(f"  FAILED user {user_spec['login']}: {error}")

        print("Projects:")
        for project_spec in fixtures.get("projects", []):
            try:
                create_project(session, project_spec)
            # Broad on purpose: one bad fixture should not stop the rest.
            except Exception as error:  # NOSONAR
                failures.append(f"project {project_spec['id']}: {error}")
                print(f"  FAILED project {project_spec['id']}: {error}")

        if failures:
            print(f"\nFinished with {len(failures)} failure(s):")
            for failure in failures:
                print(f"  - {failure}")
            raise SystemExit(1)

        print("Done.")


if __name__ == "__main__":
    try:
        main(
            os.environ["XNAT_URL"],
            os.environ["ADMIN_USERNAME"],
            os.environ["ADMIN_PASSWORD"],
            os.environ["FIXTURES"],
            os.environ["USER_PASSWORD"],
        )
    # Broad on purpose: surface a readable message in the compose log.
    except Exception as error:  # NOSONAR
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
