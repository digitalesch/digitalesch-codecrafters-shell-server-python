from typing import List
import sys
import os
import subprocess

class Shell():
    def __init__(self):
        self.available_commands = {
            'exit': self.exit,
            'echo': self.echo,
            'type': self.type,
            "pwd":  self.pwd,
            "cd":   self.cd
        }

        self.current_dir = os.getcwd()

        # Get the PATH environment variable
        self.path_var = os.environ.get("PATH", "")

        # Split it into individual directories
        self.paths = self.path_var.split(os.pathsep)  # os.pathsep is ':' on Linux/Mac, ';' on Windows

    def parse_commands(self, input: str, **kwargs):
        parts = input.strip().split(" ")
        
        return {
            "original": parts,
            "command": parts[0],
            "args": parts[1:],
        }

    def execute_command(self, args: str):
        command = self.parse_commands(args)
        try:
            return self.available_commands[command.get("command")](*command.get("args"))
        except Exception as e:
            custom_program_return = self.execute_program(*command.get("original"))
            if custom_program_return:
                return custom_program_return.returncode
            if not custom_program_return:
                sys.stdout.write(f"{command.get("command")}: command not found\n")
                return 1

    def exit(self, *args, **kwargs):
        return -1

    def echo(self, *args, **kwargs):
        print(' '.join(args))
        return 0

    def type(self, *args, **kwargs):
        
        if args[0] in self.available_commands:
            print(f"{args[0]} is a shell builtin")
        else:
            for path in self.paths:
                file_path = os.path.join(path,args[0])
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    print(f"{args[0]} is {file_path}")
                    return 0

            print(f"{args[0]}: not found")
        return 0
    
    def execute_program(self, *args, **kwargs):
        for path in self.paths:
            # print(args)
            file_path = os.path.join(path,args[0])
            if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                return subprocess.run(args)
        return None
    
    def pwd(self, *args, **kwargs):
        # print(os.getcwd())
        print(self.current_dir)
        return 0
    
    def cd(self, *args, **kwargs):
        if os.path.isabs(args[0]):
            if os.path.exists(args[0]):
                self.current_dir = args[0]
            else:
                print(f"cd: {args[0]}: No such file or directory")
        else:
            joined_path = os.path.normpath(os.path.join(self.current_dir, args[0]))
            if os.path.exists(joined_path):
                self.current_dir = joined_path
            else:
                print(f"cd: {joined_path}: No such file or directory")
        # else:
            # cd: /does_not_exist: No such file or directory
        
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
