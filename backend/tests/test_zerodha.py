
import pytest
from kiteconnect import exceptions as kite_exceptions

from app.brokers import zerodha as zerodha_module


class FakeKite:
    def __init__(self, profile_error=None):
        self.access_token = None
        self.profile_error = profile_error

    def set_access_token(self, token):
        self.access_token = token

    def profile(self):
        if self.profile_error:
            raise self.profile_error
        return {"user_id": "TEST123"}


def test_restore_saved_session(monkeypatch):
    service = zerodha_module.ZerodhaService()
    fake_kite = FakeKite()

    monkeypatch.setattr(
        zerodha_module.keyring,
        "get_password",
        lambda *args: "fake_saved_token",
    )
    monkeypatch.setattr(service, "_get_client", lambda: fake_kite)

    assert service.restore_session() is True
    assert service.is_authenticated is True
    assert fake_kite.access_token == "fake_saved_token"


def test_expired_token_is_cleared(monkeypatch):
    service = zerodha_module.ZerodhaService()
    fake_kite = FakeKite(
        profile_error=kite_exceptions.TokenException("Token expired")
    )

    deleted = []

    monkeypatch.setattr(
        zerodha_module.keyring,
        "delete_password",
        lambda *args: deleted.append(True),
    )
    monkeypatch.setattr(service, "_get_client", lambda: fake_kite)

    service._kite = fake_kite
    service._access_token = "fake_expired_token"

    with pytest.raises(RuntimeError, match="session expired"):
        service.get_profile()

    assert service.is_authenticated is False
    assert fake_kite.access_token is None
    assert deleted == [True]


def test_network_error_does_not_clear_token(monkeypatch):
    service = zerodha_module.ZerodhaService()
    fake_kite = FakeKite(
        profile_error=ConnectionError("Network unavailable")
    )

    deleted = []

    monkeypatch.setattr(
        zerodha_module.keyring,
        "delete_password",
        lambda *args: deleted.append(True),
    )
    monkeypatch.setattr(service, "_get_client", lambda: fake_kite)

    service._kite = fake_kite
    service._access_token = "fake_valid_token"

    with pytest.raises(ConnectionError):
        service.get_profile()

    assert service.is_authenticated is True
    assert deleted == []


def test_profile_success(monkeypatch):
    service = zerodha_module.ZerodhaService()
    fake_kite = FakeKite()

    monkeypatch.setattr(service, "_get_client", lambda: fake_kite)

    service._kite = fake_kite
    service._access_token = "fake_valid_token"

    result = service.get_profile()

    assert result["user_id"] == "TEST123"
    assert service.is_authenticated is True
