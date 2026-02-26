from app.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.refresh_interval_hours == 24
    assert settings.listen_host == "0.0.0.0"
    assert settings.listen_port == 8080
    assert settings.log_level == "info"


def test_custom_settings(monkeypatch):
    monkeypatch.setenv("REFRESH_INTERVAL_HOURS", "12")
    monkeypatch.setenv("LISTEN_PORT", "9090")
    settings = Settings()
    assert settings.refresh_interval_hours == 12
    assert settings.listen_port == 9090
