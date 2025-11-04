from typing import List
import sys

class Shell():
    def __init__(self):
        self.available_commands = {
            'exit': self.exit,
            'echo': self.echo,
            'type': self.type
        }

    def parse_commands(self, input: str, **kwargs):
        parts = input.split(" ")
        
        return {
            "command": parts[0],
            "args": parts[1:]
        }

    def execute_command(self, inputs: List[str]):
        command = self.parse_commands(inputs)
        try:
            return self.available_commands[command.get("command")](*command.get("args"))
        except Exception as e:
            sys.stdout.write(f"{command.get("command")}: command not found\n")
            return 1

    def exit(self, *args, **kwargs):
        # if len(args) == 1:
        #     try:
        #         value = int(args[0])
        #     except:
        #         return -1
        return -1

    def echo(self, *args, **kwargs):
        print(' '.join(args))
        return 0

    def type(self, *args, **kwargs):
        if args[0] in self.available_commands:
            print(f"{args[0]} is a shell builtin")
        else:
            print(f"{args[0]}: command not found\n")
        return 0

def main():
    # TODO: Uncomment the code below to pass the first stage
    shell = Shell()
    while True:
        sys.stdout.write("$ ")
        return_code = shell.execute_command(input())
        if return_code < 0:
            break

if __name__ == "__main__":
    main()
