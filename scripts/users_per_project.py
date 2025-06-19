import xnat
import pandas as pd
import argparse
import getpass
from datetime import datetime

def main(xnat_url, username, password, selected_project=None):
    dictionary_list = []
    today = datetime.today().strftime('%Y-%m-%d')
    csv_path = f"./{today}_XNAT_users_per_project.csv"
    
    with xnat.connect(xnat_url, user=username, password=password) as session:
        print(f"Connected to {xnat_url}")
        for project in session.projects:
            if selected_project and project.name != selected_project:
                continue
            print(f"Project: {project.name}")
            for name in project.users:
                user = project.users[name]
                pi = project.pi
    
                user_dict = {
                    "project": project.name,
                    "user_login_name": user.login,
                    "user_first_name": user.first_name,
                    "user_last_name": user.last_name,
                    "user_email": user.email,
                    "access_level": user.access_level,
                    "group": user.group,
                    "pi_firstname": pi.firstname,
                    "pi_lastname": pi.lastname,
                    "pi_title": pi.title,
                    "pi_email": pi.email,
                    "pi_institution": pi.institution,
                }
                dictionary_list.append(user_dict)
        print(f"Disconnected.")
    
    df = pd.DataFrame(dictionary_list)
    df.to_csv(csv_path, index=False)
    print(f"Output written to {csv_path}.")

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

