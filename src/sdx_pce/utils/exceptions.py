class ValidationError(Exception):
    """
    A custom exception class to indicate errors.
    """

    def __init__(self, message):
        super().__init__(message)


class UnknownRequestError(Exception):
    """
    Indicates unknown requests.
    """

    def __init__(self, message: str, request_id: str):
        """
        :param message: a string containing the error message.
        :param request_id: a string containing request ID.
        """
        super().__init__(f"{message} (ID: {request_id})")
        self.request_id = request_id
