import argparse
import getpass
import re
from datetime import datetime

import pandas as pd
import xnat

# Logins outside this character set are spam accounts; querying them makes XNAT
# return a 500, so they are skipped before the group lookup.
SAFE_LOGIN = re.compile(r"^[A-Za-z0-9._@+-]+$")

# XNAT names its project groups "{PROJECT_ID}_{level}".
ACCESS_LEVELS = {
    "owner": "Owners",
    "member": "Members",
    "collaborator": "Collaborators",
}

def get_user_profiles(session):
    """Return {login: profile} for every account, including disabled ones."""
    return {profile["username"]: profile for profile in session.get_json("/xapi/users/profiles")}

def split_group_id(group_id, project_ids):
    """Split a group id into (project_id, access_level).

    Returns (None, None) for groups that are not project groups, such as
    ALL_DATA_ADMIN. Project ids may themselves contain underscores, so the
    known ids are matched rather than splitting on the last separator.
    """
    for level in ACCESS_LEVELS:
        suffix = f"_{level}"
        if group_id.endswith(suffix):
            project_id = group_id[: -len(suffix)]
            if project_id in project_ids:
                return project_id, level
    return None, None

def get_project_memberships(session, project_ids, logins):
    """Return (memberships, skipped, failed) for the given logins.

    memberships is {project_id: {login: access_level}}. It is built from each
    user's group membership rather than from the per-project user listing,
    because that listing leaves out disabled accounts.

    skipped holds logins that were not queried because they contain unexpected
    characters; failed holds {login: error} for lookups that raised.
    """
    memberships = {project_id: {} for project_id in project_ids}
    skipped = []
    failed = {}

    for login in logins:
        if not SAFE_LOGIN.match(login):
            skipped.append(login)
            continue

        try:
            group_ids = session.get_json(f"/xapi/users/{login}/groups")
        except Exception as error:  # noqa: BLE001 - one bad account must not stop the run
            failed[login] = error
            continue

        for group_id in group_ids:
            project_id, level = split_group_id(group_id, project_ids)
            if project_id is not None:
                memberships[project_id][login] = level

    return memberships, skipped, failed

def report_problem_logins(skipped, failed):
    """Print the logins that were skipped or that failed their group lookup."""
    if skipped:
        print(f"\nSkipped {len(skipped)} login(s) with unexpected characters:")
        for login in skipped:
            print(f"  {login!r}")

    if failed:
        print(f"\nFailed to look up groups for {len(failed)} login(s):")
        for login, error in failed.items():
            print(f"  {login!r}: {error}")

def main(xnat_url, username, password, selected_project=None):
    dictionary_list = []
    today = datetime.today().strftime('%Y-%m-%d')
    csv_path = f"./{today}_XNAT_users_per_project.csv"
    
    with xnat.connect(xnat_url, user=username, password=password) as session:
        print(f"Connected to {xnat_url}")

        projects = {project.id: project for project in session.projects.values()}
        profiles = get_user_profiles(session)
        memberships, skipped, failed = get_project_memberships(session, set(projects), profiles)

        for project_id, project in projects.items():
            if selected_project and selected_project not in (project.name, project_id):
                continue
            print(f"Project: {project.name}")
            pi = project.pi

            for login, level in memberships[project_id].items():
                profile = profiles.get(login, {})

                user_dict = {
                    "project": project.name,
                    "user_login_name": login,
                    "user_first_name": profile.get("firstName"),
                    "user_last_name": profile.get("lastName"),
                    "user_email": profile.get("email"),
                    "access_level": ACCESS_LEVELS[level],
                    "group": f"{project_id}_{level}",
                    "enabled": profile.get("enabled"),
                    "verified": profile.get("verified"),
                    "pi_firstname": pi.firstname,
                    "pi_lastname": pi.lastname,
                    "pi_title": pi.title,
                    "pi_email": pi.email,
                    "pi_institution": pi.institution,
                }
                dictionary_list.append(user_dict)
        print("Disconnected.")
    
    df = pd.DataFrame(dictionary_list)
    df.to_csv(csv_path, index=False)
    print(f"Output written to {csv_path}.")

    report_problem_logins(skipped, failed)

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Extract XNAT users per project')
    parser.add_argument('--xnat_url', type=str, required=True, 
                        help='URL for the XNAT instance (e.g., https://xnat.health-ri.nl)')
    parser.add_argument('--project', type=str, required=False, 
                        help='Specific project to query (leave empty to query all projects)')
    args = parser.parse_args()

    # Prompt for username and password
    username = input("Enter your XNAT username: ")
    password = getpass.getpass("Enter your XNAT password: ")

    main(args.xnat_url, username, password, args.project)
