import copy

import pytest

from libs.parser import NewConfigParser


@pytest.fixture
def new_config_parser(test_data):
    test_data = copy.deepcopy(test_data)
    new_config_parser = NewConfigParser(
        service=test_data['service'], envname=test_data['env_name'],
        envname_shared=test_data['env_name_shared'], env_location=test_data['env_location'],
        host_info=test_data['host_info'], required_variables=test_data['required_variables'],
        config_data=test_data['service_config_template']
    )
    new_config_parser.host = test_data['host_info'][1]
    return new_config_parser


@pytest.fixture(scope="module")
def test_data():
    data = {
        'env_id': '1747',
        'env_name': 'LAB-LEM-AMS',
        'env_location': 'ams02',
        'env_name_shared': 'AMS02-Shared-Resources',
        'service': 'testy_static_service',
        'required_variables': [
            'ENV.CLEANNAME', 'ENV.POD', 'Server.location', 'SERVER_FQDN',
            'ENV.PLATFORM.IntApiURL', 'PWR.INTAPI_PORT',
            'ENV.PLATFORM.ExtApiURL', 'ENV.PLATFORM.WsgApiURL',
            'PWR.PASAPI_PORT', 'ENV.PLATFORM.PasApiURL',
            'IGL.end.point', 'ENV.DNS_ALL.RECORD_FORMAT',
            'ENV.PLATFORM.MediaURL', 'TRA.pool.group', 'TSA.pool.group'
        ],
        'host_info': {1: {
            'ENV.CLEANNAME': 'LAB-LEM-AMS',
            'ENV.POD': "02",
            'SERVER_FQDN': 'lab01-t01-tes23.mydomain',
            'Server.location': 'sjc01',
            'ENV.PLATFORM.IntApiURL': 'http://intapi-lablemams.mydomain:8082',
            'ENV.PLATFORM.ExtApiURL': 'http://extapi-lablemams.mydomain',
            'ENV.PLATFORM.WsgApiURL': 'http://wsgapi-lablemams.mydomain:8086',
            'ENV.PLATFORM.PasApiURL': 'pasapi-lablemams.mydomain',
            'PWR.INTAPI_PORT': '8082',
            'TRA.pool.group': "1",
            'TSA.pool.group': "2"
        }},
        'current_service_config': [{
            "name": "testy_static_service",
            "version": "v5",
            "serviceInterface": "rest",
            "location": "sjc01",
            "deploymentScheme": "cl-2dc",
            "address": "lab01-t01-tes23.mydomain",
            "port": 8080,
            'group': "group01",
            "order": 0,
            "ssl": False,
            "newModel": True
        }],
        'service_config_template': [{
            "serviceName": "testy_static_service",
            "serviceVersion": "v5",
            "serviceInterface": "rest",
            "deploymentScheme": "cl-2dc",
            "location": "{Server.location}",
            "physicalEnv": None,
            "ssl": False,
            "group": "group0{TRA.pool.group}",
            "address": {
                "default": "{SERVER_FQDN}",
                "shared_by_env": None,
                "shared_by_location": None,
                "source_service": None
            },
            "port": 8080
        }],
        'service_config': [{
            "serviceName": "testy_static_service",
            "serviceVersion": "v5",
            "serviceInterface": "rest",
            "deploymentScheme": "cl-2dc",
            'location': 'sfp01',
            'physicalEnv': None,
            "ssl": False,
            'group': "group01",
            "address": "lab01-t01-tes23.mydomain",
            "port": 8080,
        }],
        'deployment_schemes': [
            {'name': 'test-1dc', 'podRequired': False, 'dcPriorities': [
                {'entryDc': 'sjc01', 'activeDc': '*', 'priorities': ['sjc01', 'ams02']},
                {'entryDc': 'iad41', 'activeDc': '*', 'priorities': ['iad41', 'ams02']},
                {'entryDc': '*', 'activeDc': '*', 'priorities': ['ams02', 'iad41', 'sjc01']}
            ]},
            {'name': 'test-2dc', 'podRequired': False, 'dcPriorities': [
                {'entryDc': 'sjc01', 'activeDc': 'sjc01', 'priorities': ['sjc01', 'iad41', 'ams02']},
                {'entryDc': 'iad41', 'activeDc': 'iad41', 'priorities': ['iad41', 'sjc01', 'ams02']},
                {'entryDc': '*', 'activeDc': '*', 'priorities': ['ams02', 'iad41', 'sjc01']}
            ]}
        ],
        'deployment_schemes_template': {
            'all_dc_record': {'entryDc': '*', 'activeDc': '*', 'priorities': 'all'},
            'multipop': {
                'test-1dc': {
                    'name': 'test-1dc',
                    'podRequired': False,
                    'dcPriorities': [
                        {'entryDc': 1, 'activeDc': '*', 'priorities': [1]},
                        {'entryDc': 2, 'activeDc': '*', 'priorities': [2]}
                    ]
                },
                'test-2dc': {
                    'name': 'test-2dc',
                    'podRequired': False,
                    'dcPriorities': [
                        {'entryDc': 1, 'activeDc': 1, 'priorities': [1, 2]},
                        {'entryDc': 2, 'activeDc': 2, 'priorities': [2, 1]}
                    ]
                }
            }
        },
        'unique_pops': {1: 'sjc01', 2: 'iad41'},
        'unique_server_locs': {'sjc01', 'iad41'},
        'unique_pop_locs': {'ams02'},
        'pop_server_location': {1: {'location': 'ams02', 'server_location': 'sjc01'},
                                2: {'location': 'ams02', 'server_location': 'iad41'}},
        'env_services': {'service1': [], 'service2': []},
        'all_services': {
            'service1': [], 'service2': [{'address': {'source_service': 'service1'}}],
            'service3': [], 'service4': []
        }
    }
    return data
