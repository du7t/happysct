"""Schemes and service configs parser"""

import re

from api_libs.logger import Logger, log


logger = Logger()


@log(logger)
def parse_deployment_schemes(
        unique_pops: dict, unique_server_locs: set, unique_pop_locs: set, schemes_template: dict
) -> list:
    target_pops = {pop: value for pop, value in unique_pops.items() if pop <= 2 and value}
    env_type = "monopop" if len(target_pops) == 1 else "multipop"
    schemes_template["all_dc_record"]["priorities"] = sorted(
        list(unique_server_locs | unique_pop_locs)
    )

    for scheme in schemes_template[env_type]:
        for record in schemes_template[env_type][scheme]["dcPriorities"]:
            if isinstance(record["entryDc"], int):
                record["entryDc"] = target_pops[record["entryDc"]]
            if isinstance(record["activeDc"], int):
                record["activeDc"] = target_pops[record["activeDc"]]
            record["priorities"] = [target_pops[dc] for dc in record["priorities"]]
            record["priorities"].extend(
                loc for loc in unique_pop_locs if loc not in record["priorities"]
            )
        schemes_template[env_type][scheme]["dcPriorities"].append(schemes_template["all_dc_record"])

    return list(schemes_template[env_type].values())


class NewConfigParser(object):
    @log(logger)
    def __init__(
            self, service: str, host_info: dict, required_variables: list, config_data: list,
            envname: str, envname_shared: str = "", env_location: str = ""
    ) -> None:
        self.service = service
        self.host_info = host_info
        self.required_variables = required_variables
        self.config_data = config_data
        self.env_local_name = envname.upper()
        self.env_shared_name = envname_shared
        self.env_location = env_location.lower()

    def get_config(self) -> list:
        new_config = []
        hosts = self.host_info.values() if self.host_info else [None]
        unique_addresses = set()
        for data in self.config_data:
            for host in hosts:
                filled_data = self.fill_data(data, host)
                if filled_data["address"] not in unique_addresses:
                    new_config.append(filled_data)
                    unique_addresses.add(filled_data["address"])
        if self.validate(new_config):
            return new_config

    def validate(self, config: list) -> bool:
        for item in config:
            address = str(item.get("address", ''))
            port = item.get("port", None)
            if "{" in address or address in self.required_variables or not address:
                raise ValueError(f'service not present on env, got address {address}')
            if not isinstance(port, int) or port > 65535:
                raise ValueError(f'invalid new port, got {port}')
        return True

    @log(logger)
    def fill_data(self, data: dict, host) -> dict:
        """Fill service data by using service config and calculating fields"""
        filled_data = data.copy()
        self.host = host or {}
        filled_data["address"] = self.get_address(data["address"])
        filled_data["port"] = self.get_port(data["port"])
        filled_data["location"] = self.get_location(data.get("location")) if data.get("location") else None
        filled_data["physicalEnv"] = self.get_physical_env(data.get("physicalEnv")) if data.get("physicalEnv") else None
        filled_data["group"] = self.get_group(data.get("group")) if data.get("group") else None
        return filled_data

    @log(logger)
    def expand_variable(self, input_str: str):
        var_match = re.search(r'{([^}]*)}', input_str)
        var_name = var_match.group(1) if var_match else None
        var_value = self.host.get(var_name, "")
        return re.sub(r'({[^}]*})', var_value, input_str)

    @log(logger)
    def get_location(self, location: str) -> str:
        """Get location by host or env location"""
        return (
            self.host.get(location.strip("{}"), self.env_location).lower()
            if self.host else self.env_location
        )

    @log(logger)
    def get_physical_env(self, physical_env: str) -> str:
        """Get physical_env by host POD, default: p01"""
        return (
            f'p{self.host.get(physical_env.strip("{}"), "p01")}'
            if self.host else "p01"
        )

    @log(logger)
    def get_address(self, data: dict) -> str:
        """Get local or shared service address, conditions order matters"""
        address = data["default"].strip("{}")
        # use local if local server exists on env
        if self.host and self.host["ENV.CLEANNAME"] == self.env_local_name:
            address = self.host[address]
        # use shared if shared_by_location not null
        elif data["shared_by_location"]:
            address = data["shared_by_location"].get(self.env_location,
                                                     data["shared_by_location"]["default"])
        # use shared if shared_by_env not null
        elif data["shared_by_env"]:
            address = data["shared_by_env"].get(self.env_shared_name,
                                                data["shared_by_env"]["default"])
        # use shared if server exists on shared env or added as foreign placeholder on local env
        elif self.host:
            address = self.host[address]
        address = address.split("//")[-1].split(":")[0]
        return address

    @log(logger)
    def get_port(self, port: int | str) -> int:
        """Get port by port variable"""
        if isinstance(port, str) and "{" in port:
            port = self.host.get(port.strip("{}"), "").split(":")[-1]
            port = int(port) if port.isdecimal() else 80
        return port

    @log(logger)
    def get_group(self, group: str) -> str:
        """Get group by group variable"""
        return self.expand_variable(input_str=group)


@log(logger)
def adjust_current_config(current_conf: list) -> list:
    for item in current_conf:
        item.update(
            serviceName=item.pop("name", None),
            serviceVersion=item.pop("version", None),
            serviceInterface=item.pop("serviceInterface", None),
            deploymentScheme=item.pop("deploymentScheme", None),
            location=item.pop("location", None),
            physicalEnv=item.pop("selectedPod", None),
            ssl=item.pop("ssl", None),
            group=item.pop("group", None),
            address=item.pop("address", None),
            port=item.pop("port", None),
        )
        item.pop("pods", None)
        item.pop("newModel", None)
        item.pop("order", None)
    return sorted(current_conf, key=lambda x: x['address'])
