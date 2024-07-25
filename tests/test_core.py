from json import JSONDecodeError

from jsonschema import ValidationError
import pytest
from requests import HTTPError

from libs import core


@pytest.fixture
def mock_load_json(mocker):
    return mocker.patch("libs.core.load_json")


@pytest.fixture
def mock_validate(mocker):
    return mocker.patch("libs.core.validate")


@pytest.fixture
def mock_read_services_config(mocker, test_data):
    return mocker.patch('libs.core.read_services_config', return_value=test_data['all_services'])


@pytest.fixture
def mock_sct_manager(mocker, test_data):
    env_mock = mocker.MagicMock()
    env_mock.id = test_data['env_id']
    env_mock.name = test_data['env_name']
    mocker.patch('libs.core.ENV', return_value=env_mock)
    mocker.patch('libs.core.ADS')
    mocker.patch('libs.core.SCT')

    sct_manager = core.SCTManager(env_name=test_data['env_name'])
    sct_manager.env_services = {'service': ['current_config']}
    return sct_manager


@pytest.fixture
def mock_get_required_variables(mocker):
    return mocker.patch('libs.core.get_required_variables')


@pytest.fixture
def mock_adjust_current_config(mocker):
    return mocker.patch('libs.core.adjust_current_config', return_value=["current_config"])


@pytest.fixture
def mock_new_config_parser(mocker):
    return mocker.patch('libs.core.NewConfigParser')


@pytest.fixture
def mock_get_service_configs(mocker):
    return mocker.patch('libs.core.SCTManager.get_service_configs')


@pytest.fixture
def mock_get_unique_pops_locations(mocker, test_data):
    return mocker.patch(
        'libs.core.SCTManager.get_unique_pops_locations',
        return_value=(test_data['unique_pops'], test_data['unique_server_locs'], test_data['unique_pop_locs'])
    )


@pytest.fixture
def mock_parse_deployment_schemes(mocker, test_data):
    return mocker.patch('libs.core.parse_deployment_schemes', return_value=test_data['deployment_schemes'])


def test_read_services_config_valid(mock_load_json, mock_validate):
    mock_load_json.side_effect = [{"key": "value"}, None]
    mock_validate.side_effect = None

    result = core.read_services_config()

    assert result == {"key": "value"}


def test_read_services_config_invalid_json(mock_load_json, mock_validate, capsys):
    mock_load_json.side_effect = JSONDecodeError("JSON decode error", "", 0)
    mock_validate.side_effect = None

    with pytest.raises(SystemExit) as e:
        core.read_services_config()

    captured = capsys.readouterr()
    assert "Invalid json exception" in captured.out
    assert e.value.code == 1


def test_read_services_config_validation_error(mock_load_json, mock_validate, capsys):
    mock_load_json.side_effect = [{"key": "value"}, None]
    mock_validate.side_effect = [ValidationError("Validation error"), None]

    with pytest.raises(SystemExit) as e:
        core.read_services_config()

    captured = capsys.readouterr()
    assert "Validation error" in captured.out
    assert e.value.code == 1


def test_get_required_variables(test_data):
    assert set(core.get_required_variables()) == set(test_data['required_variables'])


def test_filter_services(mock_read_services_config, test_data):
    filtered_services = core.filter_services(
        env_services=test_data['env_services'], only='', group='', exclude='', force=False
    )
    assert filtered_services == ['service3', 'service4']


def test_filter_services_only(mock_read_services_config, test_data):
    filtered_services = core.filter_services(
        env_services=test_data['env_services'], only='service3', group='', exclude='', force=False
    )
    assert filtered_services == ['service3']


def test_filter_services_group(mock_read_services_config, test_data):
    filtered_services = core.filter_services(
        env_services=test_data['env_services'], only='', group='service1', exclude='', force=True
    )
    assert filtered_services == ['service1', 'service2']


def test_filter_services_force(mock_read_services_config, test_data):
    filtered_services = core.filter_services(
        env_services=test_data['env_services'], only=('service3', 'service1'), group='', exclude='', force=True
    )
    assert filtered_services == ['service1', 'service3']


def test_filter_services_exclude(mock_read_services_config, test_data):
    filtered_services = core.filter_services(
        env_services=test_data['env_services'], only='', group='', exclude='service3', force=False
    )

    assert filtered_services == ['service4']


def test_filter_services_no_services(mock_read_services_config, test_data):
    filtered_services = core.filter_services(
        env_services=test_data['env_services'], only='service1', group='', exclude='', force=False
    )
    assert filtered_services == []


def test_sct_manager_init(mock_sct_manager, test_data):
    assert mock_sct_manager.env_id == test_data['env_id']
    assert mock_sct_manager.env_local_name == test_data['env_name']


def test_get_service_host_info(mock_sct_manager):
    mock_sct_manager.env_local.get_service_host_by_pod.return_value = ['host1', 'host2']
    mock_sct_manager.ads.calculate_server_variables.return_value = {'var1': 'value1', 'var2': 'value2'}

    hosts_info = mock_sct_manager.get_service_host_info('service', 'source_service', ['var1', 'var2'])

    assert hosts_info == {'host1': {'var1': 'value1', 'var2': 'value2'}, 'host2': {'var1': 'value1', 'var2': 'value2'}}


def test_get_service_host_info_no_hosts(mock_sct_manager):
    mock_sct_manager.env_local.get_service_host_by_pod.return_value = []
    mock_sct_manager.ads.calculate_server_variables.return_value = {}

    hosts_info = mock_sct_manager.get_service_host_info('service', None, ['var1', 'var2'])

    assert hosts_info == {}


def test_get_service_configs(
        mock_sct_manager, test_data, mock_read_services_config, mock_get_required_variables,
        mock_adjust_current_config, mock_new_config_parser
):
    mock_read_services_config.return_value = {test_data['service']: test_data['service_config_template']}

    current_config, new_config, config_diff, message = mock_sct_manager.get_service_configs(test_data['service'])

    assert current_config == ["current_config"]
    assert new_config
    assert config_diff
    assert message == "ok"


def test_get_service_configs_value_error(
        mock_sct_manager, test_data, mock_read_services_config, mock_get_required_variables,
        mock_adjust_current_config, mock_new_config_parser
):
    mock_new_config_parser.return_value.get_config.side_effect = ValueError('Invalid new config')
    mock_read_services_config.return_value = {test_data['service']: test_data['service_config_template']}

    current_config, new_config, config_diff, message = mock_sct_manager.get_service_configs(test_data['service'])

    assert current_config == ["current_config"]
    assert new_config == []
    assert config_diff
    assert message == "Invalid new config"


def test_get_unique_pops_locations(mock_sct_manager, test_data):
    mock_sct_manager.env_local.get_pop_server_location.return_value = test_data['pop_server_location']

    unique_pops, unique_server_locs, unique_pop_locs = mock_sct_manager.get_unique_pops_locations()

    assert unique_pops == test_data['unique_pops']
    assert unique_server_locs == test_data['unique_server_locs']
    assert unique_pop_locs == test_data['unique_pop_locs']


def test_get_current(mock_sct_manager, mock_adjust_current_config):
    result = mock_sct_manager.get_current('service')

    assert result
    assert isinstance(result, list)


def test_get_diff(mock_sct_manager, mock_get_service_configs):
    mock_get_service_configs.return_value = 'current', 'new', 'diff', 'ok'

    result = mock_sct_manager.get_diff('service')

    assert result
    assert isinstance(result, dict)
    assert 'status' in result


def test_update_added(mock_sct_manager, mock_get_service_configs):
    mock_get_service_configs.return_value = 'current', 'new', 'diff', 'ok'

    result = mock_sct_manager.update(service='service')

    assert result
    assert result['message'] == 'added'
    assert result['status']


def test_update_recreated(mock_sct_manager, mock_get_service_configs):
    mock_get_service_configs.return_value = 'current', 'new', 'diff', 'ok'

    result = mock_sct_manager.update(service='service', force=True)

    assert result
    assert result['message'] == 'recreated'
    assert result['status']


def test_update_http_error(mock_sct_manager, mock_get_service_configs):
    mock_get_service_configs.return_value = 'current', 'new', 'diff', 'ok'
    mock_sct_manager.sct.update_service.side_effect = HTTPError

    result = mock_sct_manager.update(service='service')

    assert result
    assert result['message'] == 'HTTPError'
    assert not result['status']


def test_update_no_changes(mock_sct_manager, mock_get_service_configs):
    mock_get_service_configs.return_value = 'current', 'new', None, 'ok'

    result = mock_sct_manager.update(service='service')

    assert result
    assert 'no changes' in result['message']
    assert result['status']


def test_update_no_new_config(mock_sct_manager, mock_get_service_configs):
    mock_get_service_configs.return_value = 'current', None, 'diff', 'failed new config'

    result = mock_sct_manager.update(service='service')

    assert result
    assert 'failed' in result['message']
    assert not result['status']


def test_update_deployment_schemes(mock_load_json, mock_sct_manager,
                                   mock_get_unique_pops_locations, mock_parse_deployment_schemes):
    result = mock_sct_manager.update_deployment_schemes()

    assert result
    assert result['status']
    assert 'test-1dc' in result['message']
