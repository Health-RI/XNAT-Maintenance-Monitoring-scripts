from pathlib import Path
import xnat
import pandas as pd
import argparse
import getpass
from datetime import datetime

def main(xnat_url, username, password, report_path, study_overview_path):
    # Read the Disk Usage (du) output, and split it into projects:
    with open(report_path, 'r') as fname:
        lines = fname.readlines()
    
    # Remove the header
    lines.pop(0)
    # Remove empty lines
    project_list = [line.strip().split('\t') for line in lines if line != '\n']
    print(f"Number of projects in du output: {len(project_list)}")
    
    # Read in the study overview:
    study_overview = pd.read_csv(study_overview_path, sep=';')
    substudies = study_overview['substudy'].tolist()
    print(f"Number of substudies: {len(substudies)}")
    
    dictionary_list = []
    today = datetime.today().strftime('%Y-%m-%d')
    csv_path = f"./{today}_XNAT_Disk_usage.csv"
    
    with xnat.connect(xnat_url, user=username, password=password) as session:
        print(f"Connected to {xnat_url}")
        for project_usage in project_list:
            data_usage = project_usage[0]
            project_path = Path(project_usage[1])
            project_id = project_path.name
            if project_id not in substudies:
                continue
            try:
                xnat_project = session.projects[project_id]
            except KeyError:
                continue
            print(f"Project: {xnat_project.name}")
            pi = xnat_project.pi
            user_dict = {
                "project_id": project_id,
                "main_study": study_overview[study_overview['substudy'] == project_id]['main_study'].values[0],
                "project_path": project_path,
                "data_usage (MB)": data_usage,
                "xnat_project_name": xnat_project.name,
                "xnat_project_id": xnat_project.id,
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
    print(f"Number of substudies in output: {df.shape[0]}")
    print(f"Missing substudies: {[idx for idx in substudies if idx not in df.project_id.to_list()]}")


if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Extract XNAT disk usage information')
    parser.add_argument('--xnat_url', type=str, required=True, 
                        help='URL for the XNAT instance (e.g., https://xnat.health-ri.nl)')
    parser.add_argument('--report_path', type=str, required=True,
                        help='Path to the disk usage report file')
    parser.add_argument('--study_overview', type=str, required=True,
                        help='Path to the project/study overview CSV file')
    args = parser.parse_args()
    
    # Prompt for username and password
    username = input("Enter your XNAT username: ")
    password = getpass.getpass("Enter your XNAT password: ")

    main(args.xnat_url, username, password, args.report_path, args.study_overview)
