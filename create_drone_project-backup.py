import os
import argparse
import re

# to be completed, add more project types; the purpose is to setup directory 
# structure for different types of drone projects:
# 1. Vegetation Imagery
# 2. Drone Mapping
# 3. Drone Videography
# 4. Drone Photography
PROJECT_TYPES = ['Default', 'Vegetation Imagery', 'Drone Mapping', 'Drone Videography', 'Drone Photography']

def to_snake_case(name):
    name = re.sub(r'[\s\-]+', '_', name)  # Replace spaces and hyphens with underscores
    return name.lower()

def create_directory_structure(project_name):
    # Define the base directory
    base_dir = os.path.join("Drone_Videography_Projects", project_name)
    
    # Define the directory structure
    directories = [
        os.path.join(base_dir, '01_Raw_Footage', 'Drone_Videos'),
        os.path.join(base_dir, '01_Raw_Footage', 'Handheld_Photos'),
        os.path.join(base_dir, '01_Raw_Footage', 'Metadata'),
        os.path.join(base_dir, '02_Editing', 'Edited_Videos'),
        os.path.join(base_dir, '02_Editing', 'Drafts'),
        os.path.join(base_dir, '02_Editing', 'Assets', 'Audio'),
        os.path.join(base_dir, '02_Editing', 'Assets', 'Graphics'),
        os.path.join(base_dir, '03_Structure_from_Motion', 'SfM_Outputs'),
        os.path.join(base_dir, '04_Notes_and_Documentation', 'Meeting_Notes'),
        os.path.join(base_dir, '05_Deliverables', 'Client_Package'),
        os.path.join(base_dir, 'Template_Files')
    ]
    
    # Create directories
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    # Create placeholder files
    create_placeholder_files(base_dir)

def create_placeholder_files(base_dir):
    # Create placeholder Markdown file for the project proposal
    proposal_file_path = os.path.join(base_dir, 'Template_Files', 'Project_Proposal_Template.md')
    with open(proposal_file_path, 'w') as f:
        f.write("# Project Proposal\n\n")
        f.write("## Project Title: [Insert Title Here]\n\n")
        f.write("### 1. Introduction\n[Briefly describe the purpose of the project and what you aim to achieve.]\n\n")
        f.write("### 2. Objectives\n- Objective 1\n- Objective 2\n- Objective 3\n\n")
        f.write("### 3. Scope\n[Define the scope of the project, including what will and won’t be covered.]\n\n")
        f.write("### 4. Methodology\n[Outline how you plan to carry out the project, including equipment, locations, and techniques.]\n\n")
        f.write("### 5. Timeline\n| Task | Responsible | Start Date | End Date |\n|------|-------------|------------|----------|\n")
        f.write("| Task 1 | [Name] | [MM/DD/YYYY] | [MM/DD/YYYY] |\n")
        f.write("### 6. Budget\n[Provide an outline of the projected budget for the project.]\n\n")
        f.write("### 7. Deliverables\n- Deliverable 1\n- Deliverable 2\n- Deliverable 3\n\n")
        f.write("### 8. Conclusion\n[Summarize the proposal and encourage contact for further discussion.]\n\n")
        f.write("---\n\n")
        f.write("**Prepared by:** [Your Name]  \n**Date:** [MM/DD/YYYY]\n")

    # Create placeholder metadata files
    video_metadata_path = os.path.join(base_dir, '01_Raw_Footage', 'Metadata', 'Video_Metadata.csv')
    with open(video_metadata_path, 'w') as f:
        f.write("FileName,Duration,Resolution,DateCaptured\n")

    photo_metadata_path = os.path.join(base_dir, '01_Raw_Footage', 'Metadata', 'Photo_Metadata.csv')
    with open(photo_metadata_path, 'w') as f:
        f.write("FileName,DateCaptured\n")

    # Create placeholder note files
    notes_file_path = os.path.join(base_dir, '04_Notes_and_Documentation', 'Client_Details.txt')
    with open(notes_file_path, 'w') as f:
        f.write("# Client Details\n")
        f.write("Name: [Client Name]\n")
        f.write("Contact: [Client Contact Info]\n\n")
        # could incorporate questions from drone mapping course here

    # Process Notes placeholder
    processing_notes_path = os.path.join(base_dir, '03_Structure_from_Motion', 'Processing_Notes.txt')
    with open(processing_notes_path, 'w') as f:
        f.write("# Structure from Motion Processing Notes\n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create directory structure for a new drone project.")
    parser.add_argument("project_name", type=str, help="Name of the project")
    parser.add_argument("--project_path", type=str, default=".", help="Path to create the project directory")
    parser.add_argument("--project_type", type=str, default="Default", help="Type of the project", choices=PROJECT_TYPES)
    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Check args
    # -------------------------------------------------------------------------
    assert os.path.exists(args.project_path), f"Path '{args.project_path}' does not exist."
    assert args.project_type in PROJECT_TYPES, f"Invalid project type '{args.project_type}'."
    project_name = to_snake_case(args.project_name)
    project_path = os.path.join(args.project_path, project_name)
    
    create_directory_structure(project_name)
    print(f"Project directory structure for '{project_name}' created successfully!")