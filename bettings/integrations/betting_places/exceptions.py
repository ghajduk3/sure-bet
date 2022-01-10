
class XpathBaseException(Exception):
    pass


class XpathElementNotFoundException(XpathBaseException):
    pass


class XpathElementsNotFoundError(XpathBaseException):
    pass