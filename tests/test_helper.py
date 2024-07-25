import pytest
from requests.exceptions import ConnectTimeout, HTTPError, ProxyError
from requests.models import Response

from libs import helper


@pytest.fixture
def temp_file(tmp_path):
    return tmp_path / "temp.txt"


@pytest.mark.parametrize("arg", ["string", ("tup", "le"), "tra,tsa-api"])
def test_arg_to_list(arg):
    result = helper.arg_to_list(arg)
    assert isinstance(result, list)


@pytest.mark.parametrize("exc_class, result", [
    (Exception, False),
    (ProxyError, True),
    (ConnectTimeout, True)
])
def test_retry_on_exceptions(exc_class, result):
    exception = exc_class()
    assert helper.retry_on_exceptions(exception) == result


@pytest.mark.parametrize(
        ("status_code", "result"),
        [
            (503, True),
            (429, True),
            (401, False)
        ]
)
def test_retry_on_exceptions_statuses(status_code, result):
    exception = HTTPError(response=Response())
    exception.response.status_code = status_code
    assert helper.retry_on_exceptions(exception) == result


def test_load_json(temp_file):
    temp_file.write_text('{"serviceName": "ace"}')
    data = helper.load_json(temp_file)
    assert isinstance(data, dict)
