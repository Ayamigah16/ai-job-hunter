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
