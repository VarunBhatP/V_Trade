
import keyring
from keyring.errors import PasswordDeleteError
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kite_exceptions
from app.core.config import settings


SERVICE_NAME = "QuantTrader"
USERNAME = "zerodha_access_token"


class ZerodhaService:
    def __init__(self):
        self._kite = None
        self._access_token = None

    def _get_client(self):
        if not settings.KITE_API_KEY:
            raise RuntimeError("KITE_API_KEY is not configured")

        if self._kite is None:
            self._kite = KiteConnect(api_key=settings.KITE_API_KEY)

        return self._kite

    def _save_access_token(self, token: str):
        keyring.set_password(SERVICE_NAME, USERNAME, token)

    def _load_access_token(self):
        return keyring.get_password(SERVICE_NAME, USERNAME)

    def _clear_access_token(self):
        try:
            keyring.delete_password(SERVICE_NAME, USERNAME)
        except PasswordDeleteError:
            pass

        self._access_token = None

        if self._kite:
            self._kite.set_access_token(None)

    def get_login_url(self) -> str:
        return self._get_client().login_url()

    def complete_login(self, request_token: str) -> dict:
        if not settings.KITE_API_SECRET:
            raise RuntimeError("KITE_API_SECRET is not configured")

        kite = self._get_client()

        session_data = kite.generate_session(
            request_token,
            api_secret=settings.KITE_API_SECRET,
        )

        access_token = session_data.get("access_token")

        if not access_token:
            raise RuntimeError("Zerodha did not return an access token")

        self._save_access_token(access_token)

        kite.set_access_token(access_token)
        self._access_token = access_token

        return {
            "user_id": session_data.get("user_id"),
            "user_name": session_data.get("user_name"),
            "broker": session_data.get("broker"),
            "login_time": session_data.get("login_time"),
            "authenticated": True,
        }

    def restore_session(self) -> bool:
        token = self._load_access_token()

        if not token:
            return False

        self._get_client().set_access_token(token)
        self._access_token = token
        return True

    def get_profile(self) -> dict:
        if not self._access_token:
            self.restore_session()

        if not self._access_token:
            raise RuntimeError("Zerodha authentication required")

        try:
            return self._get_client().profile()

        except kite_exceptions.TokenException:
            self._clear_access_token()
            raise RuntimeError(
                "Zerodha session expired. Please log in again."
            ) from None

    def get_authenticated_client(self):
        if not self._access_token:
            self.restore_session()

        if not self._access_token:
            raise RuntimeError("Zerodha authentication required")

        return self._get_client()

    def invalidate_session(self):
        self._clear_access_token()

    @property
    def is_authenticated(self) -> bool:
        return self._access_token is not None


zerodha_service = ZerodhaService()
