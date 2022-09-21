"""
Copyright 2022 PandaAwAke

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


import logging
import re

from model import handle_error
from model.stats import stats


class GlobalOptimizer:
    """
    Take all stages, and make some global changes to the whole dockerfile.
    -   Add/Modify the syntax directive. For example, add "# syntax=docker/dockerfile:1.3".
    """

    def __init__(self):
        ...

    def optimizable(self, stages: list) -> bool:
        """
        Determine if a stage is optimizable.
        If a dockerfile does not use the official frontend, then we cannot optimize it.
        :param stages: the stages of the dockerfile.
        :return: True if this dockerfile can be optimized, or else False.
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
                syntax = self._get_syntax(s=value)
                if syntax:
                    syntax_lower = syntax.lower()
                    if not syntax_lower.startswith('docker/dockerfile:') and \
                            not syntax_lower.startswith('docker.io/docker/dockerfile:'):
                        return False
        return True

    def optimize(self, stages: list, new_stages_lines: list):
        """
        Optimize the whole dockerfile.
        :param stages: the stages of the dockerfile.
        :param new_stages_lines:
        :return: None
        """
        # Try to add "# syntax = docker/dockerfile:1.3"
        assert len(stages) > 0
        assert len(stages[0][0]) > 0
        assert len(new_stages_lines) > 0
        assert len(new_stages_lines[0][0]) > 0

        need_to_add_syntax = True
        need_to_update_syntax = False

        # Get information for syntax directive, to determine whether we need to add/update syntax
        syntax_line_index = 0
        for instruction in stages[0][0]:
            if instruction['instruction'] != 'COMMENT':
                break
            else:
                # Detect syntax
                value: str = instruction['value']
                syntax = self._get_syntax(s=value)
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

    def _get_syntax(self, s: str):
        """
        Get the value of syntax directive.
        For "# syntax=docker/dockerfile:1.3", this will return "1.3".
        If s isn't in this format, then this will return None.
        :param s: the string to parse.
        :return: value of syntax directive, or None if s isn't in syntax directive format.
        """
        # syntax directive regex
        syntax_directive_re = re.compile(r'^\s*syntax\s*=\s*(.*?)\s*$', re.I)
        match = syntax_directive_re.match(s)
        if match and len(match.groups()) > 0:
            return match.group(1)
