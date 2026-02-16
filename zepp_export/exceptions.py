"""Custom exceptions for the zepp-export library."""


class ZeppAuthError(Exception):
    """Raised when authentication fails (HTTP 401).

    This typically means the token has expired. Tokens last several weeks.
    To get a fresh token:
      1. Go to https://user.huami.com/privacy/index.html
      2. Log in with your Zepp/Amazfit account
      3. Extract the 'apptoken' from browser cookies
      4. Update your .env or ~/.zepp-export/config

    Or run: python -m zepp_export login
    """


class ZeppAPIError(Exception):
    """Raised when the API returns a non-success response.

    Attributes:
        status_code: HTTP status code (if available)
    """

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)


class ZeppDecodeError(Exception):
    """Raised when response data cannot be decoded.

    This can happen when:
    - Base64 data is malformed
    - JSON structure is unexpected
    - Binary data is truncated or corrupted
    """
