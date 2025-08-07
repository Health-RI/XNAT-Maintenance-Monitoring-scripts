from pathlib import Path
import xnat
import pandas as pd
import argparse
import getpass
from datetime import datetime

def main(xnat_url, username, password, report_paths, study_overview_path, output_folder=None):
    # Read in the study overview if provided:
    if study_overview_path:
        study_overview = pd.read_csv(study_overview_path, sep=';')
        substudies = study_overview['substudy'].tolist()
        print(f"Number of substudies: {len(substudies)}")
    else:
        study_overview = None
        substudies = None
        print("No study overview provided - processing all projects")
    
    output_files = []
    today = datetime.today().strftime('%Y-%m-%d')
    
    # Connect once and reuse the session for all reports
    with xnat.connect(xnat_url, user=username, password=password) as session:
        print(f"Connected to {xnat_url}")
        
        for i, report_path in enumerate(report_paths):
            print(f"\nProcessing report {i+1}/{len(report_paths)}: {report_path}")
            
            # Read the Disk Usage (du) output
            with open(report_path, 'r') as fname:
                lines = fname.readlines()
            
            # Remove the header
            lines.pop(0)
            # Remove empty lines
            project_list = [line.strip().split('\t') for line in lines if line != '\n']
            print(f"Number of projects in du output: {len(project_list)}")
            
            dictionary_list = []
            
            for project_usage in project_list:
                data_usage = project_usage[0]
                project_path_obj = Path(project_usage[1])
                project_id = project_path_obj.name
                if substudies and project_id not in substudies:
                    continue
                try:
                    xnat_project = session.projects[project_id]
                except KeyError:
                    continue
                print(f"Project: {xnat_project.name}")
                pi = xnat_project.pi
                if study_overview is not None:
                    main_study = study_overview[study_overview['substudy'] == project_id]['main_study'].values[0]
                else:
                    main_study = project_id
                
                user_dict = {
                    "project_id": project_id,
                    "main_study": main_study,
                    "project_path": project_path_obj,
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
            
            # Generate output filename for this report
            input_basename = Path(report_path).stem
            if output_folder:
                csv_path = Path(output_folder) / f"{today}_{input_basename}_XNAT_Disk_usage.csv"
            else:
                csv_path = f"./output/{today}_{input_basename}_XNAT_Disk_usage.csv"
            
            # Write output file for this report
            df = pd.DataFrame(dictionary_list)
            df.to_csv(csv_path, index=False)
            print(f"Output written to {csv_path}.")
            print(f"Number of entries in output: {df.shape[0]}")
            output_files.append(csv_path)
            
            if substudies:
                missing_substudies = [idx for idx in substudies if idx not in df.project_id.to_list()]
                if missing_substudies:
                    print(f"Missing substudies: {missing_substudies}")
        
        print("\nDisconnected.")
    
    print(f"\nProcessed {len(report_paths)} reports, generated {len(output_files)} output files:")
    for output_file in output_files:
        print(f"  - {output_file}")
    
    return output_files


if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Extract XNAT disk usage information')
    parser.add_argument('--xnat_url', type=str, required=True, 
                        help='URL for the XNAT instance (e.g., https://xnat.health-ri.nl)')
    parser.add_argument('--report_path', type=str, nargs='+', required=True,
                        help='Path(s) to disk usage report file(s). Each file will generate a separate output.')
    parser.add_argument('--study_overview', type=str, required=False,
                        help='Path to the project/study overview CSV file (optional)')
    parser.add_argument('--output_folder', type=str, required=False,
                        help='Custom output folder')
    args = parser.parse_args()
    
    # Prompt for username and password
    username = input("Enter your XNAT username: ")
    password = getpass.getpass("Enter your XNAT password: ")

    main(args.xnat_url, username, password, args.report_path, args.study_overview, args.output_folder)
