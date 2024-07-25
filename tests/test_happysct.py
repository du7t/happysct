import pytest

import happysct


cli = happysct.CLI()


@pytest.fixture
def mock_filter_services(mocker, test_data):
    return mocker.patch('happysct.filter_services', return_value=list(test_data['all_services']))


@pytest.fixture
def mock_sct_manager(mocker):
    return mocker.patch('happysct.SCTManager')


def test_print_diff_table(caplog):
    happysct.print_diff_table(add=[], recreate=[], skip=[], fail=['service1'])

    assert caplog.records
    assert "Fail: ['service1']" in caplog.records[-1].message


def test_cli_update(mock_sct_manager, mock_filter_services, capsys):
    cli.update('env')

    captured = capsys.readouterr()
    assert "Completed." in captured.out


def test_cli_update_schemes(mock_sct_manager, mock_filter_services):
    mock_sct_manager.return_value.update_deployment_schemes.return_value = {'status': False}

    with pytest.raises(RuntimeError) as pytest_wrapped_e:
        cli.update('env', schemes=True)

    assert "deployment schemes" in pytest_wrapped_e.value.args[0]


def test_cli_update_invalid_envname():
    with pytest.raises(Exception) as pytest_wrapped_e:
        cli.update(1)
    assert pytest_wrapped_e.value.args[0] == 'Incorrect arguments'


def test_cli_update_no_envname_typerror():
    with pytest.raises(TypeError) as pytest_wrapped_e:
        cli.update()
    assert "required argument" in pytest_wrapped_e.value.args[0]


def test_cli_diff(mock_sct_manager, mock_filter_services, capsys):
    mock_sct_manager.return_value.get_diff.return_value = {
        'status': True, 'message': 'skip', 'current_config': {}, 'new_config': {}, 'config_diff': {}
    }
    cli.diff('env')

    captured = capsys.readouterr()

    assert "No changes." in captured.out


def test_cli_show(mock_sct_manager, mock_filter_services, capsys):
    cli.show('env')

    captured = capsys.readouterr()

    assert not captured.err
