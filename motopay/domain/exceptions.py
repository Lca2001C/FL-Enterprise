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


class MercadoPagoNotConnectedError(MotoPayError):
    """Operação sem conta Mercado Pago OAuth conectada."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message or "Conta Mercado Pago não conectada para esta operação."
        )
