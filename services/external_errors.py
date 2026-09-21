class ExternalServiceError(Exception):
    """A safe, user-facing error raised by an external information source."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class MissingApiKeyError(ExternalServiceError):
    """Raised when an external service cannot run without its credential."""
