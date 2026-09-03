from app.core.config import Settings
from app.data.repository import MockDataSource, PostgresDataSource, get_data_source


def test_get_data_source_returns_mock_without_credentials() -> None:
    settings = Settings(_env_file=None)
    assert isinstance(get_data_source(settings), MockDataSource)


def test_get_data_source_returns_postgres_with_credentials() -> None:
    settings = Settings(
        _env_file=None,
        db_host="localhost",
        db_name="zevent",
        db_user="reader",
        db_password="secret",
    )
    assert isinstance(get_data_source(settings), PostgresDataSource)
