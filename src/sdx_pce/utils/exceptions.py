class ValidationError(Exception):
    """
    A custom exception to represent validation errors.
    """

    def __init__(self, message):
        super().__init__(message)


class UnknownRequestError(Exception):
    """
    A custom exception to represent unknown requests.
    """

    def __init__(self, message: str, request_id: str):
        """
        :param message: a string containing the error message.
        :param request_id: a string containing request ID.
        """
        super().__init__(f"{message} (ID: {request_id})")
        self.request_id = request_id


class TEError(Exception):
    """
    A custom exception to represent TE (Traffic Engineering) errors.
    """

    def __init__(self, message: str, te_code: int):
        """
        :param message: a string containing the error message.
        :param te_code: an integer representing the TE error code.
        """
        super().__init__(f"{message} (TE Code: {te_code})")
        self.te_code = te_code
