import dockerfile_parse.util
from model.global_status import GlobalStatus


def replace_home_char(path: str, global_status: GlobalStatus) -> str:
    """
    Replace '~' in the directory path.

    :param path: the path to be replaced.
    :param global_status: the global_status object.
    :return: replaced path.
    """
    return path.replace('~', global_status.user_dirs[global_status.user][:-1])


def get_absolute_path(path: str, global_status: GlobalStatus) -> str:
    """
    Return the absolute path of "path".
    If path is already an absolute path, then return itself.

    :param path: the relative or absolute path.
    :param global_status: the global_status object.
    :return: absolute path.
    """
    if path.startswith('/'):
        return path
    return global_status.work_dir + path


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
