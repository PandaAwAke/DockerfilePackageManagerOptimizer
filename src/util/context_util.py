import logging

import dockerfile_parse.util

from config.optimization_config import pm_settings
from model import handle_error
from model.global_status import GlobalStatus
from util import str_util


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


def get_mount_target_dirs(instruction, context) -> list:
    run_options_str, _ = str_util.separate_run_options(instruction['value'])
    run_options_str += ' '  # This operation is meaningless, just to make the code simpler
    find_index: int = 0
    find_index = run_options_str.find('--mount=type=cache', find_index)
    existing_target_dirs = []
    while find_index != -1:
        target_dir_index = run_options_str.find('target=', find_index)
        if target_dir_index == -1:
            logging.error('Cannot find the target directory in existing --mount=type=cache RUN instruction: '
                          '"{0}"'.format(instruction['content']))
            raise handle_error.HandleError()

        # Get target_dir
        space_index = run_options_str.find(' ', target_dir_index)
        if space_index == -1:
            logging.error('Illegal --mount=type=cache instruction format: '
                          '"{0}"'.format(instruction['content']))
            raise handle_error.HandleError()
        target_dir = run_options_str[target_dir_index + len('target='):space_index]
        target_dir = substitute_env(target_dir, context)
        existing_target_dirs.append(target_dir)

        find_index = run_options_str.find('--mount=type=cache', find_index + len('--mount=type=cache'))

    return existing_target_dirs


def get_context_default_cache_dirs(pm_name: str, global_status: GlobalStatus):
    return [
        replace_home_char(cache_dir, global_status)
        for cache_dir in pm_settings[pm_name].default_cache_dirs
    ]

