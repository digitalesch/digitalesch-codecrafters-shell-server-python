from main import Shell
import pytest

shell = Shell()


@pytest.fixture
def return_parsed_commands():
    def _parse(command: str):
        print(f"Parsing command {command}...")
        return shell.parse_commands(command)
    return _parse

@pytest.mark.parametrize(
    "command, expected",
    [
        ("tipo", (1, "", "tipo: command not found\n")),
        ("pwd", (0, '/mnt/c/Users/Felipe/Desktop/projects/languages/python/codecrafters-shell-python\n', '')),
        ("type cd", (0, "cd is a shell builtin\n", '')),
        ("type cat", (0, "cat is /usr/bin/cat\n", '')),
        ("exit", (-1, '','')),
        ("cd ~", (0, '','')),
        ("pwd", (0, '/home/felipe\n','')),
        ("cd /non-existing-directory", (1, '','cd: /non-existing-directory: No such file or directory\n')),
        # ("ls", (0, "README.md\napp\ncodecrafters.yml\npyproject.toml\nshell\ntext.txt\nuv.lock\nvenv\nyour_program.sh\n",'')),
        ("", (0, '','')), # no input is
        ("cat /tmp/bear", (1, '',"cat: /tmp/bear: No such file or directory\n")), # stderr since the file doesnt exist
        # ("echo 'banana' > /tmp/quz/banana", (1, "", '')),
        ('ls -1 nonexistent 2> bar.md', (2,'',"")),
        # ("cat /tmp/bar/baz.md", (1, '',"ls: nonexistent: No such file or directory")),
        ("echo 'Hello Emily' 1>> helloEmily.md", (0, "", "")),
        ("ls -1 helloEmily.md >> bar.md",(0,"", "")),
        ("echo 'Hello James' 1>> foo.md",(0, "", "" )),
        ("echo 'Hello James' 1>> foo.md",(0, "", "" )),
    ]
)
def test_execute_commands(command, expected):
    assert shell.execute_command(command) == expected