import unittest
import os

from dockerfile_parse import DockerfileParser


class TestDockerfileParser(unittest.TestCase):

    def setUp(self):
        ...

    def test_dockerfile_read_write(self):
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


if __name__ == '__main__':
    unittest.main()
