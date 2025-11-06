import sys
import os
import subprocess
import shlex

class Shell():
    def __init__(self):
        self.available_commands = {
            'exit': self.exit,
            'echo': self.echo,
            'type': self.type,
            "pwd":  self.pwd,
            "cd":   self.cd
        }
        # Gets current directory as PWD
        self.current_dir = os.getcwd()
        # Get the PATH environment variable
        self.path_var = os.environ.get("PATH", "")
        # Split it into individual directories
        self.paths = self.path_var.split(os.pathsep)  # os.pathsep is ':' on Linux/Mac, ';' on Windows


    def parse_commands(self, input: str, **kwargs):
        parts = shlex.split(input)

        file_redirect = None
        redirect = 0
        func_args = parts[1:]

        if len(parts) > 0:
            command = parts[0]
            if any(['>' in parts,'1>' in parts]):
                redirect = 1
                file_redirect = parts[-1]
                func_args = parts[1:-2]
            if ['>>'] in parts:
                redirect = 2
        else:
            command = None
            func_args = []

        return {
            "original": parts,
            "command": command,
            "args": func_args,
            "redirect": redirect,
            "file": file_redirect
        }

    def execute_command(self, args: str):
        command = self.parse_commands(args)
        # print(command)
        status_code, stdout, stderr = 0, None, None
        if command.get("command"):
            try:
                status_code, stdout, stderr = self.available_commands[command.get("command")](**command)
                # return (status_code, output)
            except Exception as e:
                # print(e)
                status_code, stdout, stderr = self.execute_program(**command)
                if status_code < 0:
                    status_code, stdout, stderr = 1, None, f"{command.get("command")}: command not found"
        if command.get("redirect") == 1:
            with open(command.get("file"),"w") as fp:
                fp.write(stdout if stdout else "") # writes empty stdout to file
                stdout = None
        
        message = stdout if status_code == 0 else stderr
        
        if message:
            # print(message, len(message))
            sys.stdout.write(message + ( "\n" if not message.endswith("\n") else ""))
        
        # general return for no input
        return (status_code,stdout, stderr)

    def exit(self, *args, **kwargs):
        return (-1, None, None)

    def echo(self, *args, **kwargs):
        return (0,' '.join(kwargs.get("args")), None)

    def type(self, *args, **kwargs):
        command_args = kwargs.get("args")[0]
        if command_args in self.available_commands:
            return (0, f"{command_args} is a shell builtin", None)
        else:
            for path in self.paths:
                file_path = os.path.join(path,command_args)
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    return (0, f"{command_args} is {file_path}", None)

            return (1, None, f"{command_args}: not found")
    
    def execute_program(self, *args, **kwargs):
        for path in self.paths:
            file_path = os.path.join(path,kwargs.get("command"))
            if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                result = subprocess.run([kwargs.get("command")] + kwargs.get("args"), capture_output=True, text=True)
                # print(result)
                return (result.returncode, result.stdout, result.stderr)
        return (-1, None, None)
    
    def pwd(self, *args, **kwargs):
        return (0, f"{self.current_dir}", None)
    
    def cd(self, *args, **kwargs):
        # gets path from kwargs args
        path = kwargs.get("args")[0]
        if path == "~":
            self.current_dir = os.getenv("HOME")
            return (0, None, None)
        if os.path.isabs(path):
            if os.path.exists(path):
                self.current_dir = path
            else:
                return (1, None, f"cd: {path}: No such file or directory")
        else:
            joined_path = os.path.normpath(os.path.join(self.current_dir, path))
            if os.path.exists(joined_path):
                self.current_dir = joined_path
            else:
                return (1, None, f"cd: {joined_path}: No such file or directory")
        
        return (0, None, None)
    
    def redirect_output(self, *args, **kwargs):
        pass

    def repl(self, *args, **kwargs):
        while True:
            sys.stdout.write("$ ")
            status_code, stdout, stderr = self.execute_command(input())
            
            if status_code < 0:
                break


def main():
    shell = Shell()
    shell.repl()

if __name__ == "__main__":
    main()
