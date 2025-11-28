import subprocess
import shlex
from dataclasses import dataclass
import readline
import os
import sys

@dataclass
class PipelineExecution:
    status_code: int = 0
    stdin: str = ""
    stdout: str = ""
    stderr: str = ""
    file_descriptor: int = None
    file: str = None

class Shell:
    def __init__(self):
        self.available_commands = {
            "exit": self.exit,
            "echo": self.echo,
            "pwd": self.pwd,
            "cd": self.cd,
            "type": self.type
        }
        self.current_dir = os.getcwd()
        self.path_var = os.environ.get("PATH", "")
        self.paths = self.path_var.split(os.pathsep)
        # self.paths = "bin/bar"
        self.executable_commands = self.list_executables()
        builtin_cmds = list(self.available_commands.keys())
        external_cmds = [cmd for cmd in self.executable_commands if cmd not in builtin_cmds]
        self.autocomplete_commands = builtin_cmds + external_cmds
        self.autocomplete_commands.sort()

        readline.set_completer(self.completer)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(' \t\n')

    # Builtin implementations
    def exit(self, **kwargs):
        return PipelineExecution(status_code=-1)

    def echo(self, **kwargs):
        output = ' '.join(kwargs.get("args", [])) + "\n"
        return PipelineExecution(
            status_code=0,
            stdout=output,
            stderr="",
            file_descriptor=kwargs.get("file_descriptor"),
            file=kwargs.get("file")
        )

    def pwd(self, **kwargs):
        return PipelineExecution(
            status_code=0,
            stdout=f"{self.current_dir}\n",
            stderr="",
            file_descriptor=kwargs.get("file_descriptor"),
            file=kwargs.get("file")
        )

    def cd(self, **kwargs):
        path = kwargs.get("args", [None])[0]
        if path is None:
            return PipelineExecution(status_code=1, stderr="cd: missing argument\n")
        if path == "~":
            self.current_dir = os.getenv("HOME")
        else:
            joined_path = path if os.path.isabs(path) else os.path.join(self.current_dir, path)
            if os.path.exists(joined_path):
                self.current_dir = os.path.normpath(joined_path)
            else:
                return PipelineExecution(status_code=1, stderr=f"cd: {joined_path}: No such file or directory\n")
        return PipelineExecution(status_code=0)

    def type(self, **kwargs):
        cmd = kwargs.get("args", [None])[0]
        if cmd in self.available_commands:
            return PipelineExecution(status_code=0, stdout=f"{cmd} is a shell builtin\n")
        for path in self.paths:
            exe = os.path.join(path, cmd)
            if os.path.isfile(exe) and os.access(exe, os.X_OK):
                return PipelineExecution(status_code=0, stdout=f"{cmd} is {exe}\n")
        return PipelineExecution(status_code=1, stderr=f"{cmd}: not found\n")

    def list_executables(self):
        binaries = []
        for path in self.paths:
            if not os.path.isdir(path):
                continue
            for f in os.listdir(path):
                fp = os.path.join(path, f)
                if os.path.isfile(fp) and os.access(fp, os.X_OK):
                    binaries.append(f)
        return binaries

    def completer(self, text, state):
        matches = [cmd for cmd in self.autocomplete_commands if cmd.startswith(text)]
        try:
            completion = matches[state]
            if len(matches) == 1:
                completion += " "
            return completion
        except IndexError:
            return None

    # Redirection mapping
    def return_file_descriptor(self, tokens):
        redirect_map = {
            '>': 1,
            '1>': 1,
            '2>': 2,
            '2>&1': 3,
            '>>': 4,
            '2>>': 5,
            "1>>": 6
        }
        for i, t in enumerate(tokens):
            if t in redirect_map and i + 1 < len(tokens):
                return tokens[i+1], redirect_map[t], i
        return None, 0, -1

    # Build pipeline dict
    def build_pipeline(self, commands):
        head = None
        for cmd in commands:
            file, fd, idx = self.return_file_descriptor(cmd)
            if file:
                execute = cmd[:idx]  # remove redirection token + target
            else:
                execute = cmd
            head = {
                "original": cmd,
                "command": execute[0],
                "args": execute[1:],  # only real arguments
                "file": file,
                "file_descriptor": fd,
                "input": head
            }
        return head


    def run_pipeline_real_pipes(self, pipeline_dict) -> PipelineExecution:
        pipeline_list = []
        pd = pipeline_dict
        while pd:
            pipeline_list.insert(0, pd)
            pd = pd.get("input")

        prev_proc = None
        procs = []
        last_result = PipelineExecution()  # <- initialize safely

        for pipe_cmd in pipeline_list:
            stdin = prev_proc.stdout if prev_proc else None

            file = pipe_cmd.get("file")
            fd = pipe_cmd.get("file_descriptor", 0)
            stdout_target = None
            stderr_target = None
            f = None

            if file:
                mode = "a" if fd in [4, 5, 6] else "w"
                f = open(file, mode)
                if fd in [1, 3, 4, 6]:
                    stdout_target = f
                if fd in [2, 3, 5]:
                    stderr_target = f

            # Built-in
            if pipe_cmd["command"] in self.available_commands:
                last_result = self.available_commands[pipe_cmd["command"]](
                    args=pipe_cmd.get("args", []),
                    file_descriptor=fd,
                    file=file
                )
                if stdout_target:
                    stdout_target.write(last_result.stdout)
                    stdout_target.flush()
                else:
                    sys.stdout.write(last_result.stdout)
                    sys.stdout.flush()

                if stderr_target:
                    stderr_target.write(last_result.stderr)
                    stderr_target.flush()
                else:
                    sys.stderr.write(last_result.stderr)
                    sys.stderr.flush()

                if f:
                    f.close()
                prev_proc = None
                continue

            # External command
            try:
                proc = subprocess.Popen(
                    [pipe_cmd["command"]] + pipe_cmd.get("args", []),
                    stdin=stdin,
                    stdout=stdout_target or subprocess.PIPE,
                    stderr=stderr_target or subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
            except FileNotFoundError:
                msg = f"{pipe_cmd['command']}: command not found\n"
                last_result = PipelineExecution(status_code=127, stderr=msg)
                if stderr_target:
                    stderr_target.write(msg)
                    stderr_target.flush()
                else:
                    sys.stderr.write(msg)
                    sys.stderr.flush()
                prev_proc = None
                continue

            if prev_proc:
                prev_proc.stdout.close()
            procs.append(proc)
            prev_proc = proc

        # Stream last process output if not redirected
        if procs:
            final_proc = procs[-1]

            if final_proc.stdout and stdout_target is None:
                for line in iter(final_proc.stdout.readline, ''):
                    sys.stdout.write(line)
                    sys.stdout.flush()

            if final_proc.stderr and stderr_target is None:
                for line in iter(final_proc.stderr.readline, ''):
                    sys.stderr.write(line)
                    sys.stderr.flush()

            for p in procs:
                p.wait()

            if f:
                f.close()

        return last_result



    # Execute commands entry
    def execute_commands(self, command: str):
        pipeline_components = [shlex.split(cmd) for cmd in command.split("|")]
        pipeline = self.build_pipeline(pipeline_components)
        return self.run_pipeline_real_pipes(pipeline)

    def repl(self):
        while True:
            try:
                command = input("$ ")
                if not command.strip():
                    continue

                # Execute the command
                result = self.execute_commands(command)

                # If the exit command was issued, break
                if isinstance(result, PipelineExecution) and result.status_code < 0:
                    break

            except EOFError:
                # Ctrl+D pressed
                print()  # move to a new line
                break
            except KeyboardInterrupt:
                # Ctrl+C pressed, just print a new prompt
                break


def main():
    shell = Shell()
    shell.repl()

if __name__ == "__main__":
    main()
