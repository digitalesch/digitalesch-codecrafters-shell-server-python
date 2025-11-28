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
            "type": self.type,
            "history": self.history
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
        self.history = []
        self.entries = 0

        readline.set_completer(self.completer)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(' \t\n')
        readline.set_history_length(1000)

    # Builtin implementations
    def history(self, **kwargs):
        # self.entries = len(self.history)
        if kwargs.get("args"):
            # print(f"Using {kwargs.get("args")}")
            try:
                self.entries = int(kwargs.get("args")[0])
            except:
                # print(self.entries)
                if kwargs.get("args")[0] == "-r":
                    with open(kwargs.get("args")[1],"r") as fp:
                        # print(fp.readlines())
                        # print(self.history)
                        lines = [(index+self.entries + 2,line.strip()) for index, line in enumerate(fp)]
                        # print(lines)
                        self.history += lines
                        for cmd in lines:
                            readline.add_history(cmd[1])
                if kwargs.get("args")[0] == "-w":
                    with open(kwargs.get("args")[1],"w") as fp:
                        fp.write('\n'.join([cmd[1] for cmd in self.history])+'\n')
                
                if kwargs.get("args")[0] == "-a":
                    # print([cmd[1] for cmd in self.history[-self.entries:]])
                    # print(len(self.history)-self.entries)
                    with open(kwargs.get("args")[1],"a") as fp:
                        fp.write('\n'.join([cmd[1] for cmd in self.history[(self.entries-len(self.history)):]])+'\n')

                self.entries = len(self.history)
                
                return PipelineExecution(status_code=0)
        
        # print(self.history)
        if len(kwargs.get("args")) == 0:
            self.entries = 0
        history_display = [f'    {index}  {cmd}' for index, cmd in self.history[-self.entries:]]
        return PipelineExecution(status_code=0, stdout='\n'.join(history_display)+'\n')

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


    def run_pipelins(self, pipeline_dict) -> PipelineExecution:
        # Flatten pipeline into list
        pipeline_list = []
        pd = pipeline_dict
        while pd:
            pipeline_list.insert(0, pd)
            pd = pd.get("input")

        last_result = PipelineExecution()
        prev_proc = None

        for idx, pipe_cmd in enumerate(pipeline_list):
            file = pipe_cmd.get("file")
            fd = pipe_cmd.get("file_descriptor", 0)
            stdout_target = None
            stderr_target = None
            f = None

            # Determine if this is the last command
            is_last = (idx == len(pipeline_list) - 1)

            # Redirection
            if file:
                mode = "a" if fd in [4, 5, 6] else "w"
                f = open(file, mode)
                if fd in [1, 3, 4, 6]:
                    stdout_target = f
                if fd in [2, 3, 5]:
                    stderr_target = f

            # Built-in
            if pipe_cmd["command"] in self.available_commands:
                # If there's a previous process, we need to consume its output first
                if prev_proc:
                    prev_proc.wait()
                    if prev_proc.stdout:
                        prev_proc.stdout.close()
                
                last_result = self.available_commands[pipe_cmd["command"]](
                    args=pipe_cmd.get("args", []),
                    file=file,
                    file_descriptor=fd
                )

                # If piped, use subprocess.PIPE
                if not is_last:
                    prev_proc = subprocess.Popen(
                        ["cat"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    prev_proc.stdin.write(last_result.stdout)
                    prev_proc.stdin.close()
                else:
                    # Last command: output to terminal/file
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
                continue

            # External command
            try:
                # Determine stdout for this process
                if is_last:
                    proc_stdout = stdout_target if stdout_target else None
                else:
                    proc_stdout = subprocess.PIPE

                proc = subprocess.Popen(
                    [pipe_cmd["command"]] + pipe_cmd.get("args", []),
                    stdin=prev_proc.stdout if prev_proc else None,
                    stdout=proc_stdout,
                    stderr=stderr_target or subprocess.PIPE,
                    text=True
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
                if f:
                    f.close()
                prev_proc = None
                continue

            # Close the previous process's stdout so it gets SIGPIPE when appropriate
            if prev_proc:
                prev_proc.stdout.close()

            prev_proc = proc

        # Wait for the last process and handle its output
        if prev_proc:
            try:
                stdout_data, stderr_data = prev_proc.communicate()
                
                # Output to terminal if not redirected
                if stdout_data and not stdout_target:
                    sys.stdout.write(stdout_data)
                    sys.stdout.flush()
                if stderr_data and not stderr_target:
                    sys.stderr.write(stderr_data)
                    sys.stderr.flush()
                    
                last_result.status_code = prev_proc.returncode
            except Exception as e:
                last_result.status_code = 1
                sys.stderr.write(f"Error: {e}\n")

        if f:
            f.close()

        return last_result

    # Execute commands entry
    def execute_commands(self, command: str):
        pipeline_components = [shlex.split(cmd) for cmd in command.split("|")]
        pipeline = self.build_pipeline(pipeline_components)
        return self.run_pipelins(pipeline)

    def repl(self):
        while True:
            try:
                command = input("$ ")
                if not command.strip():
                    continue

                # add command to history
                self.history.append((len(self.history)+1,command))

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
