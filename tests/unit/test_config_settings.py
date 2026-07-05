from ai_job_hunter.config_settings import Settings


def test_settings_defaults_with_no_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_SHEETS_SPREADSHEET_ID",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "SMTP_HOST",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings()

    assert settings.google_application_credentials is None
    assert settings.smtp_port == 587
    assert settings.score_threshold_write == 40
    assert settings.score_threshold_notify == 70


def test_settings_reads_from_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "abc123")
    monkeypatch.setenv("SCORE_THRESHOLD_NOTIFY", "80")

    settings = Settings()

    assert settings.google_sheets_spreadsheet_id == "abc123"
    assert settings.score_threshold_notify == 80


def test_settings_treats_empty_string_env_var_as_unset(monkeypatch, tmp_path):
    """Regression test: GitHub Actions injects `${{ secrets.X }}` as "" (not
    an absent variable) when secret X isn't configured. An unset SMTP_PORT
    secret should fall back to the default, not crash on int parsing."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SMTP_PORT", "")
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    monkeypatch.setenv("SCORE_THRESHOLD_WRITE", "")

    settings = Settings()

    assert settings.smtp_port == 587
    assert settings.google_sheets_spreadsheet_id is None
    assert settings.score_threshold_write == 40
