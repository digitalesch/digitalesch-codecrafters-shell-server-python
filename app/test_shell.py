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
        ("tipo", (1, "tipo: command not found")),
        ("pwd", (0, '/mnt/c/Users/Felipe/Desktop/projects/languages/python/codecrafters-shell-python')),
        ("type cd", (0, "cd is a shell builtin")),
        ("exit", (-1, None)),
        ("cd ~", (0, None)),
        ("pwd", (0, '/home/felipe')),
        ("ls", (0, "README.md\napp\ncodecrafters.yml\npyproject.toml\nshell\ntext.txt\nuv.lock\nvenv\nyour_program.sh\n")),
        ("", (0, None)) # no input is
        ("cat /tmp/bear", (0, "cat: /tmp/bear: No such file or directory")) # stderr since the file doesnt exist
    ]
)
def test_execute_commands(command, expected):
    assert shell.execute_command(command) == expected