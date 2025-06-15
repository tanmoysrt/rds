import os


def modify_systemctl_commands_for_user_mode( commands:list[list[str]]):
    uid = os.getuid()
    if uid == 0:
        return

    for command in commands:
        command.insert(1, "--user")
