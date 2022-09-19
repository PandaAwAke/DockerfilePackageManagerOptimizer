import logging
import re

from model import handle_error
from model.stats import stats


class GlobalOptimizer:

    def __init__(self):
        self.syntax_directive_re = re.compile(r'^\s*syntax\s*=\s*(.*?)\s*$', re.I)

    def optimizable(self, stages: list) -> bool:
        """
        If a dockerfile does not use the official frontend, then we cannot optimize it
        :param stages:
        :return: if this dockerfile can be optimized
        """
        assert len(stages) > 0
        assert len(stages[0][0]) > 0
        # stages is a list of (instructions, contexts)
        for instruction in stages[0][0]:
            if instruction['instruction'] != 'COMMENT':
                break
            else:
                # Detect syntax
                value: str = instruction['value']
                syntax = self._get_syntax(value=value)
                if syntax:
                    syntax_lower = syntax.lower()
                    if not syntax_lower.startswith('docker/dockerfile:') and \
                            not syntax_lower.startswith('docker.io/docker/dockerfile:'):
                        return False
        return True

    def optimize(self, stages: list, new_stages_lines: list):
        # Try to add "# syntax = docker/dockerfile:1.3"
        assert len(stages) > 0
        assert len(stages[0][0]) > 0
        assert len(new_stages_lines) > 0
        assert len(new_stages_lines[0][0]) > 0

        need_to_add_syntax = True
        need_to_update_syntax = False
        """
        {"instruction": "FROM",       # always upper-case
             "startline": 0,              # 0-based
             "endline": 0,                # 0-based
             "content": "From fedora\n",
             "value": "fedora"},
        """
        # Get information for #syntax, to determine whether we need to add/update syntax
        syntax_line_index = 0
        for instruction in stages[0][0]:
            if instruction['instruction'] != 'COMMENT':
                break
            else:
                # Detect syntax
                value: str = instruction['value']
                syntax = self._get_syntax(value=value)
                if syntax:
                    syntax_lower = syntax.lower()
                    official_dockerfile_version = ''
                    need_to_add_syntax = False
                    if syntax_lower.startswith('docker/dockerfile:'):
                        official_dockerfile_version = syntax_lower[len('docker/dockerfile:'):]
                    elif syntax_lower.startswith('docker.io/docker/dockerfile:'):
                        official_dockerfile_version = syntax_lower[len('docker.io/docker/dockerfile:'):]
                    else:
                        logging.error('This dockerfile uses a non-official frontend, I cannot handle this.')
                        raise handle_error.HandleError()
                    versions = official_dockerfile_version.split('.')
                    if len(versions) == 1 and versions[0] != '0':      # dockerfile:1
                        need_to_update_syntax = False
                        continue
                    elif len(versions) >= 2:    # dockerfile:1.2
                        if versions[0] != '0' and int(versions[1]) < 3:
                            need_to_update_syntax = True
                    break
            syntax_line_index += 1

        if need_to_add_syntax:
            new_stages_lines[0].insert(0, '# syntax=docker/dockerfile:1.3\n')
            stats.syntax_change()  # Stats
        elif need_to_update_syntax:
            new_stages_lines[0][syntax_line_index] = '# syntax=docker/dockerfile:1.3\n'
            stats.syntax_change()  # Stats

    def _get_syntax(self, value: str):
        # syntax directive regex
        match = self.syntax_directive_re.match(value)
        if match and len(match.groups()) > 0:
            return match.group(1)
