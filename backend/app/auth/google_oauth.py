from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import settings


def verify_google_id_token(token: str) -> dict:
    """Verify a Google ID token (OIDC JWT) sent from the frontend's Sign-In
    button, and return its decoded claims (sub, email, name, picture).

    verify_oauth2_token already checks the signature, expiry, audience and
    that the issuer is Google.
    """
    try:
        return google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise ValueError(f"Invalid Google ID token: {exc}") from exc
