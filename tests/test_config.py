from app.core.config import Settings


def test_defaults_to_mock_data_without_db_credentials() -> None:
    settings = Settings(_env_file=None)
    assert settings.use_mock_data is True
    assert settings.has_db_credentials is False


def test_uses_real_data_once_all_db_fields_are_set() -> None:
    settings = Settings(
        _env_file=None,
        db_host="localhost",
        db_name="zevent",
        db_user="reader",
        db_password="secret",
    )
    assert settings.has_db_credentials is True
    assert settings.use_mock_data is False


def test_database_url_escapes_special_characters_in_password() -> None:
    settings = Settings(
        _env_file=None,
        db_host="localhost",
        db_port=5432,
        db_name="zevent",
        db_user="reader",
        db_password="p@ss/word:1",
    )
    url = settings.database_url
    assert url.password == "p@ss/word:1"
    assert url.drivername == "postgresql+psycopg"
