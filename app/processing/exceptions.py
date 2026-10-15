from uuid import UUID


class PermanentProcessingError(Exception):
    """Исключение для постоянных ошибок."""


class PaymentNotFoundError(PermanentProcessingError):
    """Исключение для отсутствующего в базе платежа."""

    def __init__(self, payment_id: UUID):
        self.payment_id = payment_id
        super().__init__(f'Payment {payment_id} not found')


class RetryableProcessingError(Exception):
    """Исключение для временных ошибок."""
