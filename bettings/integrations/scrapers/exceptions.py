
class XpathBaseException(Exception):
    pass


class XpathGeneralException(XpathBaseException):
    pass


class XpathElementNotFoundException(XpathBaseException):
    pass


class XpathElementsNotFoundError(XpathBaseException):
    pass


class XpathFrameNotFoundException(XpathBaseException):
    pass


class BetIntegrationGeneralException(Exception):
    pass


class UnableToSwitchPageError(BetIntegrationGeneralException):
    pass


class BetIntegrationClientNotFound(BetIntegrationGeneralException):
    pass