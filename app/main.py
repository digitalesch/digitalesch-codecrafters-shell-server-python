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
        'exit': exit,
        'echo': echo
    }
    command = parse_commands(inputs)
    try:
        return available_commands[command.get("command")](*command.get("args"))
    except Exception as e:
        sys.stdout.write(f"{command.get("command")}: command not found\n")
        return 1

def exit(*args, **kwargs):
    # if len(args) == 1:
    #     try:
    #         value = int(args[0])
    #     except:
    #         return -1
    return -1

def echo(*args, **kwargs):
    print(' '.join(args))
    return 0

def main():
    # TODO: Uncomment the code below to pass the first stage
    while True:
        sys.stdout.write("$ ")
        return_code = execute_command(input())
        if return_code < 0:
            break

if __name__ == "__main__":
    main()
