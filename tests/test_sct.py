import pytest
from requests import HTTPError

import libs.sct as sct_wrapper


sct = sct_wrapper.SCT()


@pytest.fixture(scope="module")
def services(test_data):
    return sct.get_services(test_data['env_id'])


@pytest.fixture(scope="module")
def deployment_schemes(test_data):
    return sct.get_deployment_schemes(test_data['env_id'])


@pytest.fixture
def response_class():
    class Response():
        def __init__(self, status_code, headers) -> None:
            self.status_code = status_code
            self.headers = headers

        def raise_for_status(self):
            return True
    return Response


@pytest.fixture
def response_failed(response_class):
    return response_class(302, {'Content-Type': 'text/html'})


@pytest.fixture
def response_ok(request, response_class):
    return response_class(request.param[0], request.param[1])


def test_check_response_valid_failed(response_failed):
    with pytest.raises(HTTPError):
        sct.check_response_valid(response_failed)


@pytest.mark.parametrize(
        "response_ok",
        [
            (204, {'Content-Type': 'application/json'}),
            (204, {'Content-Type': 'text/html'}),
            (302, {'Content-Type': 'application/json'})
        ],
        indirect=True)
def test_check_response_valid_ok(response_ok):
    try:
        sct.check_response_valid(response_ok)
    except HTTPError as e:
        assert False, f"Raised an exception {e}"


def test_check_args(test_data):
    with pytest.raises(ValueError):
        sct.check_args(int(test_data['env_id']), test_data['service'])


def test_update_service(test_data):
    assert sct.update_service(test_data['service'], test_data['env_id'],
                              test_data['service_config'])


def test_get_services(services):
    assert isinstance(services, dict)
    assert len(services) > 0


def test_delete_service(test_data, services, mocker):
    mocker.patch("libs.sct.SCT.get_services", return_value=services)
    assert sct.delete_service(test_data['service'], test_data['env_id'])


def test_get_deployment_schemes(deployment_schemes):
    assert isinstance(deployment_schemes, list)
    assert len(deployment_schemes) > 0


def test_update_deployment_schemes(test_data):
    assert sct.update_deployment_schemes(test_data['env_id'], test_data['deployment_schemes'])


def test_invalid_sct_cred(test_data):
    sct.session.auth = ("user", "password")
    check_sct_api = sct.session.get(
        f'{sct.sct_url}/service-discovery/v1/env/{test_data["env_id"]}/refs'
    )
    assert check_sct_api.headers['Content-Type'] == 'text/html'
