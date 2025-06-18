class TVDataError(Exception):
    """Raised when data refresh fails."""


class TVConnectionError(Exception):
    """Raised when TradingView API request fails."""

    def __init__(
        self, status: int, url: str, method: str, reason: str | None = None
    ) -> None:
        self.status = status
        self.url = url
        self.method = method.upper()
        self.reason = reason
        message = f"HTTP {status} for {self.method} {url}"
        if reason:
            message += f": {reason}"
        super().__init__(message)
