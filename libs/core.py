"""Core module to glue everything together"""

import json
import os
import re
import sys

from jsondiff import diff
from jsonschema import validate, ValidationError
import requests
from retrying import retry

from libs.ads_wrapper import ENV, ADS
from libs.helper import get_ff, load_json, retry_on_exceptions, arg_to_list
from api_libs.logger import Logger, log
from libs.parser import NewConfigParser, adjust_current_config, parse_deployment_schemes
from libs.sct import SCT


logger = Logger()


def read_services_config(file_name: str = "services.json") -> dict:
    """Read and validate services json config"""
    services_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "..", "conf", file_name)
    schema_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "conf", "services_schema.json")
    try:
        services_config = load_json(services_file_path)
        services_schema = load_json(schema_file_path)
        validate(instance=services_config, schema=services_schema)
        return services_config
    except json.JSONDecodeError as error:
        logger.log.exception(f'Invalid json exception: {error}')
        sys.exit(1)
    except ValidationError as error:
        logger.log.exception(f'Validation services json by schema exception: {error}')
        sys.exit(1)


def get_required_variables() -> list:
    """Get variables by parsing services json config"""
    variables = {"ENV.CLEANNAME"}
    for serv in read_services_config().values():
        for d in serv:
            variables.update({re.search(r'{([^}]*)}', value).group(1) for value in [
                d["address"]["default"], d["port"], d["location"], d["physicalEnv"], d["group"]
            ] if "{" in str(value)})
    return list(variables)


@log(logger)
def filter_services(env_services: dict, only, group, exclude, force: bool | None) -> list:
    """Filter services to process"""
    all_services = read_services_config()
    logger.log.info(f"Force mode set to {force}")
    # show case
    if force is None:
        filtered_services = list(all_services.keys())
    # need to add only new services, that doesn't exist on env, if force = False
    else:
        filtered_services = [service for service in all_services if force or service not in env_services]

    if only:
        only = arg_to_list(only)
        logger.log.info(f"Only these services are included: {only}")
        filtered_services = [service for service in filtered_services if service in only]
    elif group:
        group = arg_to_list(group)
        logger.log.info(f"These groups of services are included: {group}")
        filtered_services = [
            service for service in filtered_services
            if service in group or any(item['address']['source_service'] in group for item in all_services[service])
        ]
    elif exclude:
        exclude = arg_to_list(exclude)
        logger.log.info(f"These services are excluded: {exclude}")
        filtered_services = [service for service in filtered_services if service not in exclude]

    filtered_services.sort()

    log_message = f"Services to process: {filtered_services}" if filtered_services else "No services to process."
    logger.log.info(log_message)

    return filtered_services


class SCTManager(object):
    @retry(stop_max_attempt_number=get_ff("RETRY_COUNT"), stop_max_delay=10000, wait_fixed=1000,
           retry_on_exception=retry_on_exceptions)
    @log(logger)
    def __init__(self, env_name: str) -> None:
        self.env_local = ENV(name=env_name, user=get_ff("USER_NAME"), pwd=get_ff("USER_PASSWORD"), caching=False)
        self.env_id = str(self.env_local.id)
        self.env_local_name = self.env_local.name.upper()
        self.env_location = self.env_local.getlocation().lower()
        self.shared_env_name = self.env_local.get_shared_env() or "AMS02-Shared-Resources"
        self.env_shared = ENV(name=self.shared_env_name, user=get_ff("USER_NAME"),
                              pwd=get_ff("USER_PASSWORD"), caching=False)
        self.ads = ADS(user=get_ff("USER_NAME"), pwd=get_ff("USER_PASSWORD"), caching=False)
        logger.log.info((f"{self.env_local_name} - id: {self.env_id}, "
                         f"location: {self.env_location}, shared: {self.shared_env_name}"))
        self.sct = SCT()
        self.env_services = self.sct.get_services(envid=self.env_id)

    @retry(stop_max_attempt_number=get_ff("RETRY_COUNT"), stop_max_delay=10000, wait_fixed=2000,
           retry_on_exception=retry_on_exceptions)
    @log(logger)
    def update(self, service: str, force: bool = False) -> dict:
        """
        Add or recreate service config on env.

        :param force: If true - add new services and recreate existing.
        """
        _, new_config, config_diff, message = self.get_service_configs(service)
        old_deleted, updated, status = False, False, True
        # no need to add or update service if no diff with its current config
        if config_diff and new_config:
            try:
                # no need to delete service before adding if it doesn't exist on env
                if force and service in self.env_services:
                    logger.log.debug((f"{service} - deleting old service from sct..."))
                    old_deleted = self.sct.delete_service(service=service, envid=self.env_id)
                    logger.log.debug((f"{service} - adding service to sct..."))
                    updated = self.sct.update_service(service=service, envid=self.env_id,
                                                      input_data=new_config)
                    message = "recreated" if old_deleted and updated else None
                else:
                    logger.log.debug((f"{service} - adding service to sct..."))
                    updated = self.sct.update_service(service=service, envid=self.env_id,
                                                      input_data=new_config)
                    message = "added" if updated else None
            except requests.HTTPError as e:
                logger.log.error((f"{service} - HTTP error: {e}"))
                message = "HTTPError"
                status = False
        elif not config_diff and new_config:
            message = "no changes, nothing to update"
        elif not new_config:
            status = False
        result = {'status': status, 'message': message, 'updated': updated,
                  'old_deleted': old_deleted, 'config_diff': config_diff}
        logger.log.info(f"{service} - {result}")
        return result

    @retry(stop_max_attempt_number=get_ff("RETRY_COUNT"), stop_max_delay=10000, wait_fixed=2000,
           retry_on_exception=retry_on_exceptions)
    @log(logger)
    def get_diff(self, service: str) -> dict:
        """
        Show service difference between current config on env and new generated one.
        """
        current_config, new_config, config_diff, message = self.get_service_configs(service)
        result = {'status': bool(new_config), 'message': message, 'current_config': current_config,
                  'new_config': new_config, 'config_diff': config_diff}
        logger.log.info((f"{service} - {result}"))
        return result

    @log(logger)
    def get_current(self, service: str) -> list:
        """Get service current config."""
        result = adjust_current_config(self.env_services.get(service, []))
        logger.log.info((f"{service} - {result}"))
        return result

    @log(logger)
    def update_deployment_schemes(self) -> dict:
        """Update deployment schemes on env."""
        unique_pops, unique_server_locs, unique_pop_locs = self.get_unique_pops_locations()
        logger.log.info(f"POPs: {unique_pops}, locations: {unique_server_locs}")
        schemes_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "conf", "deployment_schemes.json")
        schemes_template = load_json(schemes_file_path)

        logger.log.info(("Parsing deployment schemes template..."))
        parsed_schemes = parse_deployment_schemes(
            unique_pops, unique_server_locs, unique_pop_locs, schemes_template
        )
        parsed_schemes_names = [scheme['name'] for scheme in parsed_schemes]
        logger.log.info((f"Parsed: {parsed_schemes_names}"))

        logger.log.info(("Updating deployment schemes in sct..."))
        status = self.sct.update_deployment_schemes(envid=self.env_id, input_data=parsed_schemes)
        result = {'status': status, 'message': parsed_schemes_names}
        logger.log.info(f"Schemes update - {result}")
        return result

    @log(logger)
    def get_service_host_info(self, service: str, source_service: str | None,
                              required_variables: list) -> dict:
        """
        Get host info by looking servers with role source_service or service.
        Searches on local env first, if not - on shared env
        """
        logger.log.debug((f"{service} - getting service host info..."))
        if source_service:
            local_hosts_fqdn = (self.env_local.get_service_host_by_pod(source_service) or
                                self.env_local.get_service_host_by_pod(service))
            if local_hosts_fqdn:
                hosts_fqdn = local_hosts_fqdn
            else:
                hosts_fqdn = (self.env_shared.get_service_host_by_pod(source_service) or
                              self.env_shared.get_service_host_by_pod(service))
        else:
            hosts_fqdn = (self.env_local.get_service_host_by_pod(service) or
                          self.env_shared.get_service_host_by_pod(service))
        logger.log.debug((f"{service} - service hosts: {hosts_fqdn}"))
        hosts_info = {}
        for host in hosts_fqdn:
            host_info = self.ads.calculate_server_variables(
                host=host, variables=required_variables
            )
            hosts_info[host] = host_info
        logger.log.debug((f"{service} - hosts variables: {hosts_info}"))
        return hosts_info

    @log(logger)
    def get_service_configs(self, service: str) -> tuple:
        """Get service current, new and diff configs"""
        assert service in read_services_config(), f"{service} does not exist in services.json"
        config_data = read_services_config()[service]
        required_variables = get_required_variables()
        service_host_info = self.get_service_host_info(
            service, config_data[0]["address"]["source_service"], required_variables
        )
        current_config = adjust_current_config(self.env_services.get(service, []))
        try:
            new_config = NewConfigParser(
                service=service, host_info=service_host_info, required_variables=required_variables,
                config_data=config_data, envname=self.env_local_name,
                envname_shared=self.shared_env_name, env_location=self.env_location
            ).get_config()
            logger.log.debug((f"{service} - service new config: {new_config}"))
            message = "ok"
        except ValueError as error:
            new_config = []
            message = str(error)
        config_diff = diff(current_config, new_config, syntax='symmetric', marshal=True)
        logger.log.debug((f"{service} - service configs diff: {config_diff}"))
        return current_config, new_config, config_diff, message

    @log(logger)
    def get_unique_pops_locations(self) -> tuple:
        """Get pops and server locations for env"""
        pops_locations = self.env_local.get_pop_server_location()
        unique_pops = dict()
        unique_server_locs = set()
        unique_pop_locs = set()
        for key, value in pops_locations.items():
            server_location = value['server_location']
            if server_location and server_location not in unique_server_locs:
                unique_server_locs.add(server_location)
                unique_pops[key] = value['server_location']
        for pop in pops_locations.values():
            unique_pop_locs.add(pop['location'])
        return unique_pops, unique_server_locs, unique_pop_locs
