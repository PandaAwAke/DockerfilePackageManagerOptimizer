import unittest

from dockerfile_parse import DockerfileParser


class TestDockerfileParser(unittest.TestCase):

    def setUp(self):
        self.parser = DockerfileParser('tmp')

    def _get_lines_structure(self, lines: list) -> list:
        self.parser.lines = [line + '\n' for line in lines]
        instructions = self.parser.structure
        self.parser = DockerfileParser('tmp')  # Clear
        return instructions

    def test_dockerfile_read_write_fileobj(self):
        with open('dockerfiles/Dockerfile.read', 'rb') as f:
            parser = DockerfileParser(fileobj=f)
            s = parser.structure
            print(s)
        with open('dockerfiles/Dockerfile.write', 'wb') as f:
            parser = DockerfileParser(fileobj=f)
            parser.lines = [
                "# comment\n",                # single-line comment
                " From  \\\n",                # mixed-case
                "   base\n",                  # extra ws, continuation line
                " #    another   comment\n",  # extra ws
                " label  foo  \\\n",          # extra ws
                "# interrupt LABEL\n",        # comment interrupting multi-line LABEL
                "    bar  \n",                # extra ws, instruction continuation
                "USER  {0}\n".format('root'),
                "# comment \\\n",             # extra ws
                "# with \\ \n",               # extra ws with a space
                "# backslashes \\\\ \n",      # two backslashes
                "#no space after hash\n",
                "# comment # with hash inside\n",
                "RUN command1\n",
                "RUN command2 && \\\n",
                "    command3\n",
                "RUN command4 && \\\n",
                "# interrupt RUN\n",          # comment interrupting multi-line RUN
                "    command5\n",
            ]

    def test_arg_env(self):
        lines = [
            'ARG arg1=bar',
            'env HOME=/root/$arg1',
            'ARG arg2',
            'ENV version=${arg2:-v1.0.0}',
            'ENV HOME1=/${arg1}/foo',
            'ENV HOME2=$HOME1/foo',
            'RUN [ "echo", "$HOME" ]',
            'RUN echo $HOME'
        ]
        s = self._get_lines_structure(lines)
        pass

    def test_run_exec_form(self):
        lines = [
            'RUN --mount=type=cache [ "/bin/bash", "-c", "echo hello" ]'
        ]
        s = self._get_lines_structure(lines)
        pass


if __name__ == '__main__':
    unittest.main()
