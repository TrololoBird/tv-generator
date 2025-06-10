import pytest
import requests_mock


@pytest.fixture
def tv_api_mock():
    with requests_mock.Mocker() as m:
        yield m
