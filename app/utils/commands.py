from typing import List
import sys

def parse_commands(input: str, **kwargs):
    parts = input.split(" ")
    
    return {
        "command": parts[0],
        "args": parts[1:]
    }

def execute_command(inputs: List[str]):
    available_commands = {
        'exit': exit
    }
    command = parse_commands(inputs)
    # print(f"CMD is: {command}")
    try:
        return available_commands[command.get("command")](*command.get("args"))
    except Exception as e:
        # print(e)
        sys.stdout.write(f"{command.get("command")}: command not found\n")
        return 1
    

def exit(*args, **kwargs):
    value = 0
    if len(args) == 1:
        try:
            value = int(args[0])
        except:
            return 1
    return value