class MotoPayError(Exception):
    """Base application error."""


class NotFoundError(MotoPayError):
    pass


class ForbiddenError(MotoPayError):
    pass


class ConflictError(MotoPayError):
    pass


class UnauthorizedError(MotoPayError):
    pass
