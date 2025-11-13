import rl.readline as readline
import sys

# List of possible completions
COMMANDS = ['hello', 'world', 'help', 'quit']

def completer(text, state):
    """
    Custom completer function.
    `text` is the current word to be completed.
    `state` is an integer for successive calls (0, 1, 2, ...).
    """
    options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None

# 1. Set the completer function
readline.set_completer(completer)

# 2. Enable completion on the Tab key
# This line is often necessary to tell readline to use the completion mechanism
readline.parse_and_bind("tab: complete")

# 3. Set the character to append after a *single* unique completion
# Here we set it to a space character ' '
readline.set_completion_append_character(' ')

# 4. Prompt for input and test
try:
    while True:
        line = input('Prompt> ')
        if line == 'quit':
            break
        print(f'You entered: {line}')
except (EOFError, KeyboardInterrupt):
    print("\nExiting.")

