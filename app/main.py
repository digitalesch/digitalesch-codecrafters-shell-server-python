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
            if '2>' in parts:
                redirect = 2
            if '2>&1' in parts:
                redirect = 3
            if redirect > 0:
                file_redirect = parts[-1]
                func_args = parts[1:-2]
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
        status_code, stdout, stderr = 0, "", ""
        if command.get("command"):
            try:
                status_code, stdout, stderr = self.available_commands[command.get("command")](**command)
            except Exception as e:
                # print(e)
                status_code, stdout, stderr = self.execute_program(**command)
                if status_code < 0:
                    status_code, stdout, stderr = 1, "", f"{command.get("command")}: command not found"
        
        
        # print(stderr, stdout, len(stderr), len(stdout))
        if command.get("redirect") > 0:
            with open(command.get("file"),"w") as fp:
                if command.get("redirect") == 1:
                    redirect_output = stdout if stdout else ""
                    stdout = None
                if command.get("redirect") == 2:
                    redirect_output = stderr if stderr else ""
                    stderr = None
                if command.get("redirect") == 3:
                    redirect_output = stdout + stderr
                    stdout, stderr = None, None
                # stdout_stderr = stdout | stderr
                fp.write(redirect_output) # writes empty stdout to file

        # heres the error, im assuming that streams are exclusive
        # but "cat a.txt b.txt 2> c.txt" when a exists and b not, should print stdout and redirect stderr
        # if cmd ok -> stdout
        # if cmd err -> stderr
        # if cmd ok 1> then stdout to redirect
        # if cmd err 1> then stderr to out and nothing to redirect
        # if cmd ok 2> then stdout and nothing to redirect
        # if cmd err 2> then nothing to stdout and stderr to redirect
        message = ""
        if stdout:
            message += stdout
        if stderr:
            message += stderr

        if message:
            sys.stdout.write(message + ( "\n" if not message.endswith("\n") else ""))
        
        # general return for no input
        return (status_code,stdout, stderr)

    def exit(self, *args, **kwargs):
        return (-1, "", "")

    def echo(self, *args, **kwargs):
        return (0,' '.join(kwargs.get("args")), "")

    def type(self, *args, **kwargs):
        command_args = kwargs.get("args")[0]
        if command_args in self.available_commands:
            return (0, f"{command_args} is a shell builtin", "")
        else:
            for path in self.paths:
                file_path = os.path.join(path,command_args)
                if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                    return (0, f"{command_args} is {file_path}", "")

            return (1, "", f"{command_args}: not found")
    
    def execute_program(self, *args, **kwargs):
        for path in self.paths:
            file_path = os.path.join(path,kwargs.get("command"))
            if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
                result = subprocess.run([kwargs.get("command")] + kwargs.get("args"), capture_output=True, text=True)
                # print(result)
                return (result.returncode, result.stdout, result.stderr)
        return (-1, "", "")
    
    def pwd(self, *args, **kwargs):
        return (0, f"{self.current_dir}", "")
    
    def cd(self, *args, **kwargs):
        # gets path from kwargs args
        path = kwargs.get("args")[0]
        if path == "~":
            self.current_dir = os.getenv("HOME")
            return (0, "", "")
        if os.path.isabs(path):
            if os.path.exists(path):
                self.current_dir = path
            else:
                return (1, "", f"cd: {path}: No such file or directory")
        else:
            joined_path = os.path.normpath(os.path.join(self.current_dir, path))
            if os.path.exists(joined_path):
                self.current_dir = joined_path
            else:
                return (1, "", f"cd: {joined_path}: No such file or directory")
        
        return (0, "", "")


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
