import logging
import re

from model import handle_error
from model.command_word import CommandWord
from util import str_util, context_util


def is_exec_form(s: str):
    """
    Check if s is exec-form string, such as '["bash", "-c", "echo 3"]'
    :param s: the string to check.
    :return: True if s is exec-form, else False.
    """
    exec_form_re = re.compile(r'^\s*(\[[\s\S]*])\s*$')
    match_result = exec_form_re.match(s)
    return match_result is not None


def match_double_quotes(s: str, start: int = 0):
    """
    Get the ending index of the firstly encountered double quotes (in s[start:]).
    If no matches, return -1.

    :param s: the string to search.
    :param start: the start index of s.
    :return: the ending index of firstly encountered double quotes, or -1 when no matches.
    """
    i = start
    while i < len(s):
        if s[i] == '"':
            j = i + 1
            while True:
                matched_quote = s.find('"', j)  # Find matched quote
                if matched_quote == -1:
                    return -1

                if s[matched_quote - 1] != '\\':
                    return matched_quote
                else:
                    j = matched_quote + 1
        i += 1
    return -1


def connect_shell_command_string(commands: list, connectors: list) -> str:
    """
    Join the full commands string using connectors.
    The length of connectors should be len(commands_str) - 1.

    :param commands: the list of command strings.
    :param connectors: the connectors to connect command strings.
    :return: the full connected commands string.
    """
    assert len(connectors) == len(commands) - 1 or len(commands) == 0
    if len(commands) == 0:
        return ''
    commands_str = commands[0]
    for index in range(len(connectors)):
        commands_str += ' {0} {1}'.format(connectors[index], commands[index + 1])
    return commands_str


def _process_command_quotes_and_words(commands_str: str):
    """
    Parse the commands_str behind RUN (shell-form).
    All command words inside commands_str (connected with &&, ||, ;, etc) will be returned.
    Note: escape character will not be translated inside double quotes, but \" inside
          double quotes will not be recognized as the end of the double quote.
          ENV variables will not be substituted.

    Examples:
    ->  apt-get install python3-pip && echo "hello, world!"
    <-  [
            CommandWord('apt-get'), CommandWord('install'), CommandWord('python3-pip'),
            CommandWord('&&'), CommandWord('echo'), CommandWord('hello, world!', DOUBLE_QUOTED)
        ]
    ->  echo 'ab\"cd' && echo "ab\"cd"
    <-  [
            CommandWord('echo'), CommandWord('ab\\"cd', SINGLE_QUOTED), CommandWord('&&'),
            CommandWord('echo'), CommandWord('ab\\"cd', DOUBLE_QUOTED)
        ]

    :param commands_str: the shell-form commands string, for example 'apt-get update && apt install gcc'
    :return: commands, connectors.
    """
    # Handling shell-form
    commands_str_split_words = []

    # - Handling quotes and brackets
    i = 0
    content_outside_quote = ''
    while i < len(commands_str):
        if commands_str[i] in ("'", '"') and \
                (i == 0 or (i > 0 and commands_str[i - 1] != '\\')):
            # Find matched quote
            if commands_str[i] == "'":
                matched_quote = commands_str.find("'", i + 1)
            else:
                matched_quote = match_double_quotes(commands_str, i)

            if matched_quote == -1:
                logging.error('Illegal RUN command: "{0}"'.format(commands_str))
                raise handle_error.HandleError()

            if len(content_outside_quote.strip()) == 0:
                commands_str_split_words.append(CommandWord(content_outside_quote))
            content_outside_quote = ''

            content_inside_quote = commands_str[i + 1: matched_quote]

            commands_str_split_words.append(
                CommandWord(content_inside_quote,
                            CommandWord.SINGLE_QUOTED if commands_str == "'" else CommandWord.DOUBLE_QUOTED))
            i = matched_quote
        else:
            content_outside_quote += commands_str[i]
        i += 1
    if len(content_outside_quote) > 0:
        commands_str_split_words.append(CommandWord(content_outside_quote))

    return commands_str_split_words


def split_command_strings(commands_str: str):
    """
    Preprocess the commands_str behind RUN (shell-form).
    The returned commands will be represented as strings.
    All commands inside commands_str (connected with &&, ||, ;, etc) will be returned.
    Note: escape character will not be translated inside double quotes, but \" inside
          double quotes can be recognized.
          ENV variables will not be substituted.

    Examples:
    ->  apt-get install python3-pip && echo "hello, world!"
    <-  (['apt-get install python3-pip', 'echo "hello, world!"'], ['&&'])
    ->  echo 'ab\"cd' && echo "ab\"cd"
    <-  (["echo 'ab\\\"cd'", 'echo "ab"cd"'], ['&&'])

    :param commands_str: the shell-form commands string, for example 'apt-get update && apt install gcc'
    :return: commands, connectors.
            commands is a list of commands (a command is a list of strings).
            connectors is a list of connectors between commands ('&&', ';', '||').
    """
    commands_str_split_words = _process_command_quotes_and_words(commands_str)

    # - Separate multiple commands in commands_str, for example 'a && b || c'
    commands = []
    connectors = []
    command_str = ''
    for command_word in commands_str_split_words:
        if command_word.kind == CommandWord.SINGLE_QUOTED:
            command_str += "'{}'".format(command_word.s)
        elif command_word.kind == CommandWord.DOUBLE_QUOTED:
            command_str += '"{}"'.format(command_word.s)
        elif command_word.kind in (CommandWord.NORMAL, CommandWord.EXEC_FORM_ARG):
            s = command_word.s
            connector_indices_kinds = []
            for connector in ('&&', ';', '||'):
                connector_index = s.find(connector)
                while connector_index != -1:
                    connector_indices_kinds.append((connector_index, connector))
                    connector_index = s.find(connector, connector_index + 1)
            connector_indices_kinds = sorted(connector_indices_kinds, key=lambda x: x[0])

            pre_connector_end_index = 0
            for connector_index, connector_kind in connector_indices_kinds:
                command_str += s[pre_connector_end_index: connector_index]
                commands.append(command_str)
                connectors.append(connector_kind)
                pre_connector_end_index = connector_index + len(connector_kind)
                command_str = ''
            command_str += s[pre_connector_end_index:]
    commands.append(command_str)
    return commands, connectors


def process_shell_form(commands_str: str, context):
    """
    Preprocess the commands_str behind RUN (shell-form).
    The returned commands will be represented as CommandWord objects.
    All commands inside commands_str (connected with &&, ||, ;, etc) will be returned.
    Note: escape character will not be translated inside double quotes, but \" inside
          double quotes can be recognized.
          ENV variables are substituted too (including string inside double quotes).
          Brackets outside quotes will be removed.

    Examples:
    ->  apt-get install python3-pip && echo "hello, world!"
    <-  ([
            [CommandWord('apt-get'), CommandWord('install'), CommandWord('python3-pip')],
            [CommandWord('echo'), CommandWord('hello, world!', DOUBLE_QUOTED)]
        ], ['&&'])
    ->  echo 'ab\"cd' && echo "ab\"cd"
    <-  ([
            [CommandWord('echo'), CommandWord('ab\\"cd', SINGLE_QUOTED)],
            [CommandWord('echo'), CommandWord('ab\\"cd', DOUBLE_QUOTED)]
        ], ['&&'])

    :param commands_str: the shell-form commands string, for example 'apt-get update && apt install gcc'
    :param context: the context of this instruction. Context can be None.
    :return: (commands, connectors).
            commands is a list of commands (a command is a list of CommandWords).
            connectors is a list of connectors between commands ('&&', ';', '||').
    """

    commands_str_split_words = _process_command_quotes_and_words(commands_str)

    # - Separate multiple commands in commands_str, for example 'a && b || c'
    commands = []
    connectors = []

    command_words = []
    for command_word in commands_str_split_words:
        if command_word.kind == CommandWord.SINGLE_QUOTED:
            command_words.append(command_word)
        elif command_word.kind == CommandWord.DOUBLE_QUOTED:
            command_word.s = context_util.substitute_env(command_word.s, context)
            command_words.append(command_word)
        elif command_word.kind in (CommandWord.NORMAL, CommandWord.EXEC_FORM_ARG):
            s = command_word.s

            # Remove brackets directly, because we don't care about the order of evaluation
            s = str_util.remove_brackets(s)
            s = context_util.substitute_env(s, context)

            connector_indices_kinds = []

            for connector in ('&&', ';', '||'):
                connector_index = s.find(connector)
                while connector_index != -1:
                    connector_indices_kinds.append((connector_index, connector))
                    connector_index = s.find(connector, connector_index + 1)
            connector_indices_kinds = sorted(connector_indices_kinds, key=lambda x: x[0])

            pre_connector_end_index = 0
            for connector_index, connector_kind in connector_indices_kinds:
                command_words.extend([
                    CommandWord(word) for word in s[pre_connector_end_index: connector_index].strip().split()
                ])

                commands.append(command_words)
                connectors.append(connector_kind)
                pre_connector_end_index = connector_index + len(connector_kind)
                command_words = []

            command_words.extend([
                CommandWord(word) for word in s[pre_connector_end_index:].strip().split()
            ])
    commands.append(command_words)
    return commands, connectors

