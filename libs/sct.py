"""SCT API wrapper"""

import requests

from libs.helper import get_ff
from api_libs.logger import Logger, log


logger = Logger()


COMMENT = f"happysct - {get_ff('USER_NAME')}"


class SCT:
    def __init__(self) -> None:
        self.sct_url = get_ff('SCT_URL')
        self.sct_auth = {'username': get_ff('SCT_USER'), 'password': get_ff('SCT_PASS')}
        self.sct_request_headers = {'Content-Type': 'application/json'}
        self.session = self._create_authenticated_session()

    @log(logger)
    def _create_authenticated_session(self) -> requests.Session:
        session = requests.Session()
        # basic auth
        session.auth = tuple(self.sct_auth.values())
        session.headers.update = self.sct_request_headers
        self._login_to_sct(session)
        return session

    @log(logger)
    def _login_to_sct(self, session) -> None:
        # get jwtSCTToken
        request_login = session.post(f'{self.sct_url}/login', data=self.sct_auth, timeout=5)
        request_login.raise_for_status()

    def check_response_valid(self, response: requests.models.Response) -> None:
        response.raise_for_status()
        # PLA-66067 - SCT API returns 200-300 on invalid auth
        if (response.status_code != 204 and
                response.headers['Content-Type'] != self.sct_request_headers['Content-Type']):
            raise requests.HTTPError("Check your SCT credentials")

    def check_args(self, env_id: str, service: str = "") -> None:
        if not (env_id and isinstance(env_id, str)) or not (isinstance(service, str)):
            raise ValueError("Check your arguments")

    @log(logger)
    def get_services(self, envid: str = "") -> dict:
        self.check_args(envid)
        response = self.session.get(
            f'{self.sct_url}/service-discovery/v1/env/{envid}/sdi/services/current'
        )
        self.check_response_valid(response)
        return response.json()

    @log(logger)
    def update_service(self, service: str, envid: str = "", input_data: list = []) -> bool:
        self.check_args(envid, service=service)
        service_data = {
            "comment": COMMENT,
            "services": input_data
        }
        response = self.session.post(
            f'{self.sct_url}/service-discovery/v1/env/{envid}/services/registration',
            json=service_data
        )
        self.check_response_valid(response)
        return response.ok

    @log(logger)
    def delete_service(self, service: str, envid: str = "") -> bool:
        self.check_args(envid, service=service)

        current_service = self.get_services(envid=envid).get(service, [])
        response = None

        for item in current_service:
            item["serviceVersion"] = item["version"]
            item["physicalEnv"] = item.get("selectedPod", None)
            item["comment"] = COMMENT

            response = self.session.post(
                f'{self.sct_url}/service-discovery/v1/env/{envid}/services/{service}/delete',
                json=item
            )
            self.check_response_valid(response)

        return response.ok if response else False

    @log(logger)
    def get_deployment_schemes(self, envid: str = "") -> dict:
        self.check_args(envid)
        response = self.session.get(
            f'{self.sct_url}/service-discovery/v1/env/{envid}/sdi/deployment-schemes'
        )
        self.check_response_valid(response)
        return response.json()

    @log(logger)
    def update_deployment_schemes(self, envid: str = "", input_data: list = []) -> bool:
        self.check_args(envid)
        deployment_schemes_data = {
            "comment": COMMENT,
            "deploymentSchemes": input_data
        }
        response = self.session.post(
            f'{self.sct_url}/service-discovery/v1/env/{envid}/deployment-schemes/registration',
            json=deployment_schemes_data
        )
        self.check_response_valid(response)
        return response.ok
