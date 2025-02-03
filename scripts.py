from bot import commands
from constants import Command

def convert_commands_for_botfather(include_admin_only:bool):
    """Convert commands to the format that BotFather accepts for /setcommands"""
    converted = [
        f"{command.command[1:]} - {command.description}"
        for command in commands
        if include_admin_only or not command.admin_only
    ]
    return "\n".join(converted)

def archive_db():
    pass

def visualise_db():
    pass

if __name__ == "__main__":
    out = convert_commands_for_botfather(False)
    print(out)