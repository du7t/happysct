import copy

import pytest

from libs.parser import parse_deployment_schemes, adjust_current_config


def test_parse_deployment_schemes(test_data):
    parsed_schemes = parse_deployment_schemes(
        unique_pops=test_data['unique_pops'], unique_server_locs=test_data['unique_server_locs'],
        unique_pop_locs=test_data['unique_pop_locs'], schemes_template=test_data['deployment_schemes_template']
    )
    assert isinstance(parsed_schemes, list)
    assert parsed_schemes == test_data['deployment_schemes']


@pytest.mark.parametrize(
    ("input_str", "expected_str"),
    [
        ("group01", "group01"),
        ("group0{TRA.pool.group}", "group01"),
        ("group0{TSA.pool.group}4", "group024"),
    ]
)
def test_expand_variable(new_config_parser, input_str, expected_str):
    assert new_config_parser.expand_variable(input_str) == expected_str


@pytest.mark.parametrize(
    ("host_info", "location_input", "location_expected"),
    [
        ({'Server.location': 'sjc01'}, "{Server.location}", "sjc01"),
        ({}, "{Server.location}", "ams02"),
    ]
)
def test_get_location(new_config_parser, host_info, location_input, location_expected):
    new_config_parser.host = host_info
    assert new_config_parser.get_location(location_input) == location_expected


@pytest.mark.parametrize(
    ("host_info", "physical_env_input", "physical_env_expected"),
    [
        ({'ENV.POD': '03'}, "{ENV.POD}", "p03"),
        ({}, "{ENV.POD}", "p01"),
    ]
)
def test_get_physical_env(new_config_parser, host_info, physical_env_input, physical_env_expected):
    new_config_parser.host = host_info
    assert new_config_parser.get_physical_env(physical_env_input) == physical_env_expected


@pytest.mark.parametrize(
    ("host_info", "address_input", "address_expected"),
    [
        (
            {'ENV.CLEANNAME': 'LAB-LEM-AMS', 'SERVER_FQDN': 'local01-t01-tst01'},
            {'default': '{SERVER_FQDN}'},
            "local01-t01-tst01"
        ),
        (
            {'ENV.CLEANNAME': 'LAB-LEM-AMS', 'ENV.PLATFORM.MediaURL': 'https://media-pla.com'},
            {'default': '{ENV.PLATFORM.MediaURL}'},
            "media-pla.com"
        ),
        (
            {'ENV.CLEANNAME': 'LAB-LEM-AMS', 'ENV.PLATFORM.MediaURL': 'http://media-pla.com'},
            {'default': '{ENV.PLATFORM.MediaURL}'},
            "media-pla.com"
        ),
        (
            {'ENV.CLEANNAME': 'LAB-LEM-AMS', 'ENV.PLATFORM.MediaURL': 'http://media-pla.com:8080'},
            {'default': '{ENV.PLATFORM.MediaURL}'},
            "media-pla.com"
        ),
        (
            {'ENV.CLEANNAME': 'AMS02-Shared-Resources', 'SERVER_FQDN': 'foreign01-t01-tst01'},
            {'default': '{SERVER_FQDN}', 'shared_by_env': None, 'shared_by_location': None},
            "foreign01-t01-tst01"
        ),
        (
            {},
            {'default': '{SERVER_FQDN}', 'shared_by_env': None, 'shared_by_location':
             {'default': 'aws01-t01-tst01', 'ams02': 'ams02-location-tst99'}},
            "ams02-location-tst99",
        ),
        (
            {},
            {'default': '{SERVER_FQDN}', 'shared_by_env': {'default': 'mb-env',
                                                           'AMS02-Shared-Resources': 'ams02-env'},
             'shared_by_location': None},
            "ams02-env",
        ),
    ]
)
def test_get_address(new_config_parser, host_info, address_input, address_expected):
    new_config_parser.host = host_info
    assert new_config_parser.get_address(address_input) == address_expected


@pytest.mark.parametrize(
    ("port_input", "port_expected"),
    [
        (8080, 8080),
        (80, 80),
        ("{PWR.INTAPI_PORT}", 8082),
        ("{ENV.PLATFORM.WsgApiURL}", 8086),
        ("{ENV.PLATFORM.ExtApiURL}", 80),
        ("{ENV.PLATFORM.PasApiURL}", 80),
        ("{Variable.not.exists}", 80),
    ]
)
def test_get_port(port_input, port_expected, new_config_parser):
    assert new_config_parser.get_port(port_input) == port_expected


def test_fill_service_config(new_config_parser, test_data):
    filled_data = new_config_parser.fill_data(new_config_parser.config_data[0], new_config_parser.host)
    assert isinstance(filled_data, dict)
    assert len(filled_data) >= 1
    assert "serviceName" in filled_data.keys()
    assert filled_data == test_data['service_config'][0]


def test_validate_service_config(new_config_parser, test_data):
    assert new_config_parser.validate(test_data['service_config'])


@pytest.mark.parametrize("field", ["address", "port"])
def test_validate_service_config_raise(new_config_parser, test_data, field):
    config = copy.deepcopy(test_data["service_config"])
    config[0][field] = "{variable}"
    with pytest.raises(ValueError):
        new_config_parser.validate(config)


def test_get_config(new_config_parser, test_data):
    assert new_config_parser.get_config() == test_data['service_config']


def test_adjust_current_config(test_data):
    current_config = adjust_current_config(test_data['current_service_config'])
    assert isinstance(current_config, list)
    assert len(current_config) >= 1
    assert isinstance(current_config[0], dict)
    assert "serviceVersion" in current_config[0].keys()
    assert "order" not in current_config[0].keys()
    assert current_config == test_data['service_config']
