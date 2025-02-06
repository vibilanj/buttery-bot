import argparse
import os
import shutil

from constants import ARCHIVE_DIR, AVAIL_CMDS, DB_FILE
from datetime import datetime

def convert_commands_for_botfather(include_admin_only:bool):
    """Convert commands to the format that BotFather accepts for /setcommands"""
    converted = [
        f"{command.command[1:]} - {command.description}"
        for command in AVAIL_CMDS
        if include_admin_only or not command.admin_only
    ]
    return "\n".join(converted)

def archive_db():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    archive_path = os.path.join(ARCHIVE_DIR, f"{timestamp}.db")
    
    try:
        shutil.copy(DB_FILE, archive_path)
        print(f"Database successfully archived to {archive_path}")
    except FileNotFoundError:
        print(f"Error: {DB_FILE} does not exist.")
    except Exception as e:
        print(f"An error occurred while archiving: {e}")

def visualise_db():
    # select file from archive?
    # read from db and make statistics and plots
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    archive_parser = subparsers.add_parser("archive", help="Archive the database")
    visualise_parser = subparsers.add_parser("visualize", help="Visualize the database")

    args = parser.parse_args()
    if args.command == "archive":
        archive_db()
    elif args.command == "visualize":
        visualise_db()
    else:
        # print(convert_commands_for_botfather(False))j
        parser.print_help()