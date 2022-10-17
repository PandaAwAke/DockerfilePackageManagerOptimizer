import re

from model.command_word import CommandWord


def remove_brackets(s: str) -> str:
    return s.replace('(', '').replace(')', '')


def separate_run_options(commands_str: str):
    """
    Separate RUN options, such as --mount=type=cache
    Example:
        For "--mount=type=cache,... --mount=type=bind,... echo 3",
        this will return ("--mount=type=cache,... --mount=type=bind,...", "echo 3")
    :param commands_str: string of commands.
    :return: (run_options_string, pure_commands_string)
    """
    remove_run_option_re = re.compile('^\s*((--\S+\s*)*)([\s\S]*?)\s*$')
    match_result = remove_run_option_re.match(commands_str)
    return match_result.group(1).strip(), match_result.group(3)


def separate_instruction_type_body(instruction_str: str):
    """
    Separate instruction's type and its body.
    Note: "body" includes run/copy options.
    Example:
        For "RUN --mount=type=cache,... echo 3",
        this will return ("RUN", "--mount=type=cache,... echo 3")

    :param instruction_str: the full string of the instruction.
    :return: (instruction_type, )
    """
    inst_re = re.compile(r'^\s*(\S+)\s+([\s\S]*)$')
    m = inst_re.match(instruction_str)
    return m.groups()


def join_command_words(command_words: list) -> str:
    """
    Join the list of CommandWord objects to string.
    :param command_words: a list of command word objects.
    :return: joined string.
    """

    command_str_list = []
    for cw in command_words:
        if cw.kind in (CommandWord.NORMAL, CommandWord.EXEC_FORM_ARG) and len(cw.s.strip()) > 0:
            command_str_list.append(cw.s)
        elif cw.kind == CommandWord.SINGLE_QUOTED:
            command_str_list.append("'{}'".format(cw.s))
        elif cw.kind == CommandWord.DOUBLE_QUOTED:
            command_str_list.append('"{}"'.format(cw.s))
    return ' '.join(command_str_list)
