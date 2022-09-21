class CommandWord:
    """
    Describe a word inside a command.
    """

    NORMAL = 0
    SINGLE_QUOTED = 1
    DOUBLE_QUOTED = 2
    EXEC_FORM_ARG = 3
    # EXECUTABLE = 4

    def __init__(self, s: str, kind=NORMAL):
        """
        Initialize the command word.
        :param s: the string of the word.
        :param kind: the kind of the word, should be one of CommandWord.NORMAL,
                    CommandWord.SINGLE_QUOTED, CommandWord.DOUBLE_QUOTED, CommandWord.EXEC_FORM_ARG.
        """
        self.s = s
        self.kind = kind

    def __str__(self):
        return self.s

    def __repr__(self):
        return self.s
