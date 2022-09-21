class HandleError(Exception):
    """
    An exception class, raised when an error occurred when processing.
    """
    def __init__(self):
        super().__init__()
