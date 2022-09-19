class CommandWord:

    NORMAL = 0
    SINGLE_QUOTED = 1
    DOUBLE_QUOTED = 2
    EXEC_FORM_ARG = 3
    # EXECUTABLE = 4

    def __init__(self, s: str, kind=NORMAL):
        self.s = s
        self.kind = kind

    def __str__(self):
        return self.s

    def __repr__(self):
        return self.s
