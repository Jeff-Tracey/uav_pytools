#!/usr/bin/env python3
"""
create_drone_project.py

Create directory structures for DJI drone photogrammetry projects.

Three modes:

  Default (one-off mission):
    Creates a self-contained dated project directory:
    YYYYMMDD_site-name_mission-type/

  --new-site (repeat monitoring site):
    Creates a site-level directory with planning/ at the top level and an
    initial dated visit folder inside visits/:
    site-name_mission-type/
      planning/
      visits/YYYYMMDD/

  --add-visit (add visit to existing site):
    Adds a new dated visit folder to an existing site directory's visits/.

Usage:
    # One-off mission (today's date)
    python create_drone_project.py rancho-mission-canyon ms-mapping

    # One-off mission (specific date)
    python create_drone_project.py rancho-mission-canyon ms-mapping --date 20260506

    # New repeat monitoring site
    python create_drone_project.py rancho-mission-canyon ms-mapping --new-site

    # Add a visit to an existing site
    python create_drone_project.py rancho-mission-canyon ms-mapping --add-visit

    # Any mode with checklist file
    python create_drone_project.py rancho-mission-canyon ms-mapping --checklist /path/to/checklist.pdf

    # Specify output location
    python create_drone_project.py rancho-mission-canyon ms-mapping --project-path /path/to/projects
"""

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path


# --- Mission types ---

MISSION_TYPES = [
    'ms-mapping',       # Mavic 3M multispectral orthophoto
    'rgb-mapping',      # RGB orthophoto
    'ms-rgb-mapping',   # Both multispectral and RGB
    '3d-model',         # 3D structure / point cloud
    'survey',           # General survey mission
]


# --- Helpers ---

def slugify(name: str) -> str:
    """Convert a name to lowercase-hyphenated slug."""
    name = name.strip().lower()
    name = re.sub(r'[\s_]+', '-', name)
    name = re.sub(r'[^\w\-]', '', name)
    name = re.sub(r'-+', '-', name)
    return name


def today_stamp() -> str:
    return date.today().strftime('%Y%m%d')


def visit_dirs(visit_path: Path) -> None:
    """Create subdirectories for a single visit (date-stamped folder)."""
    subdirs = [
        'field_notes',
        'raw_data',
        'working_data',
        'webodm_output/orthophoto',
        'webodm_output/dsm',
        'webodm_output/dtm',
        'webodm_output/pointcloud',
        'webodm_output/model3d',
        'gis',
        'deliverables',
    ]
    for d in subdirs:
        (visit_path / d).mkdir(parents=True, exist_ok=True)

    # Placeholder processing notes
    notes = visit_path / 'processing_notes.md'
    if not notes.exists():
        notes.write_text(
            f"# Processing Notes\n\n"
            f"**Visit:** {visit_path.name}\n\n"
            "## Images Removed\n\n"
            "| Index | Reason |\n"
            "|-------|--------|\n\n"
            "## WebODM Settings\n\n"
            "- Quality:\n"
            "- Feature type:\n"
            "- Other:\n\n"
            "## Notes\n\n"
        )


def planning_dirs(planning_path: Path) -> None:
    """Create planning subdirectories."""
    for d in ['checklists', 'airspace', 'flight_path']:
        (planning_path / d).mkdir(parents=True, exist_ok=True)


def copy_checklist(checklist: Path, planning_path: Path) -> None:
    """Copy checklist file into planning/checklists/."""
    if not checklist.exists():
        print(f"WARNING: Checklist file not found: {checklist}", file=sys.stderr)
        return
    dest = planning_path / 'checklists' / checklist.name
    shutil.copy2(checklist, dest)
    print(f"  Checklist copied → {dest.relative_to(dest.parent.parent.parent)}")


# --- Modes ---

def create_oneoff(site: str, mission: str, stamp: str,
                  project_path: Path, checklist: Path | None) -> None:
    """Create a self-contained single-visit project directory."""
    name = f"{stamp}_{site}_{mission}"
    root = project_path / name

    if root.exists():
        print(f"ERROR: Directory already exists: {root}", file=sys.stderr)
        sys.exit(1)

    root.mkdir(parents=True)
    planning = root / 'planning'
    planning_dirs(planning)
    visit_dirs(root)

    if checklist:
        copy_checklist(checklist, planning)

    print(f"Created one-off mission project: {root}")
    _print_tree(root)


def create_new_site(site: str, mission: str, stamp: str,
                    project_path: Path, checklist: Path | None) -> None:
    """Create a new repeat monitoring site directory with an initial visit."""
    name = f"{site}_{mission}"
    root = project_path / name

    if root.exists():
        print(f"ERROR: Site directory already exists: {root}\n"
              f"       Use --add-visit to add a new visit.", file=sys.stderr)
        sys.exit(1)

    root.mkdir(parents=True)
    planning = root / 'planning'
    planning_dirs(planning)

    visit_path = root / 'visits' / stamp
    visit_dirs(visit_path)

    if checklist:
        copy_checklist(checklist, planning)

    print(f"Created new monitoring site: {root}")
    _print_tree(root)


def add_visit(site: str, mission: str, stamp: str,
              project_path: Path, checklist: Path | None) -> None:
    """Add a new dated visit to an existing site directory."""
    name = f"{site}_{mission}"
    root = project_path / name

    if not root.exists():
        print(f"ERROR: Site directory not found: {root}\n"
              f"       Use --new-site to create it first.", file=sys.stderr)
        sys.exit(1)

    visits = root / 'visits'
    visits.mkdir(exist_ok=True)

    visit_path = visits / stamp
    if visit_path.exists():
        print(f"ERROR: Visit directory already exists: {visit_path}", file=sys.stderr)
        sys.exit(1)

    visit_dirs(visit_path)

    if checklist:
        copy_checklist(checklist, root / 'planning')

    print(f"Added visit {stamp} to site: {root}")
    _print_tree(visit_path)


# --- Display ---

def _print_tree(root: Path, prefix: str = '', is_last: bool = True) -> None:
    """Print a simple directory tree."""
    connector = '└── ' if is_last else '├── '
    if prefix:
        print(prefix + connector + root.name + '/')
    else:
        print(root.name + '/')

    children = sorted(p for p in root.iterdir())
    dirs = [p for p in children if p.is_dir()]
    files = [p for p in children if p.is_file()]
    all_items = dirs + files

    for i, item in enumerate(all_items):
        last = (i == len(all_items) - 1)
        extension = '    ' if is_last else '│   '
        child_prefix = prefix + extension
        child_connector = '└── ' if last else '├── '
        if item.is_dir():
            print(child_prefix + child_connector + item.name + '/')
        else:
            print(child_prefix + child_connector + item.name)


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(
        description="Create directory structure for a drone photogrammetry project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # One-off mission (today's date)
  python create_drone_project.py rancho-mission-canyon ms-mapping

  # One-off mission (specific date)
  python create_drone_project.py rancho-mission-canyon ms-mapping --date 20260506

  # New repeat monitoring site + first visit
  python create_drone_project.py rancho-mission-canyon ms-mapping --new-site

  # Add a visit to an existing site
  python create_drone_project.py rancho-mission-canyon ms-mapping --add-visit

  # Any mode with a checklist file
  python create_drone_project.py rancho-mission-canyon ms-mapping --checklist ~/checklists/mavic3m.pdf
        """
    )

    parser.add_argument('site', type=str,
                        help='Site name (e.g. rancho-mission-canyon)')
    parser.add_argument('mission_type', type=str, choices=MISSION_TYPES,
                        help='Mission type')
    parser.add_argument('--project-path', type=Path, default=Path('.'),
                        help='Parent directory for the project (default: current directory)')
    parser.add_argument('--date', type=str, default=None,
                        help='Date stamp YYYYMMDD (default: today)')

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--new-site', action='store_true',
                      help='Create a new repeat monitoring site')
    mode.add_argument('--add-visit', action='store_true',
                      help='Add a new visit to an existing site')

    parser.add_argument('--checklist', type=Path, default=None,
                        help='Path to checklist file to copy into planning/checklists/')

    args = parser.parse_args()

    # Validate
    if not args.project_path.exists():
        print(f"ERROR: Project path does not exist: {args.project_path}", file=sys.stderr)
        sys.exit(1)

    site = slugify(args.site)
    mission = slugify(args.mission_type)
    stamp = args.date if args.date else today_stamp()

    if args.date and not re.match(r'^\d{8}$', args.date):
        print(f"ERROR: Date must be in YYYYMMDD format, got: {args.date}", file=sys.stderr)
        sys.exit(1)

    checklist = args.checklist.resolve() if args.checklist else None

    if args.new_site:
        create_new_site(site, mission, stamp, args.project_path.resolve(), checklist)
    elif args.add_visit:
        add_visit(site, mission, stamp, args.project_path.resolve(), checklist)
    else:
        create_oneoff(site, mission, stamp, args.project_path.resolve(), checklist)


if __name__ == '__main__':
    main()
