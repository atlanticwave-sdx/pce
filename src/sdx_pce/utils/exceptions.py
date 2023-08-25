class ValidationError(Exception):
    """
    A custom exception class to indicate errors.
    """

    def __init__(self, message):
        super().__init__(message)
