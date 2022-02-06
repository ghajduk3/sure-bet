

class ApiClientError(Exception):
    pass


class ClientBadResponseCodeError(ApiClientError):
    pass


class InvalidMatchDataError(Exception):
    pass


class ApiNoDataError(ApiClientError):
    pass
