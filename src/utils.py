import dockerfile_parse.util


def substitute_env(s: str, context) -> str:
    """
    Substitute environment variables inside s using context.

    :param s: the string to be processed.
    :param context: the context object of this instruction.
    :return: processed string.
    """
    if context is None or not isinstance(context, dockerfile_parse.util.Context):
        return s
    need_to_substitute_keys = []
    for key, _ in context.envs.items():
        if (s.find('${' + key + '}') != -1 or s.find('$' + key) != -1) and \
                key not in need_to_substitute_keys:
            need_to_substitute_keys.append(key)
    for key in need_to_substitute_keys:
        value = context.envs[key]
        s = s.replace('${' + key + '}', value)
        s = s.replace('$' + key, value)
    return s
