import pytest

import rollout


@pytest.fixture
def mock_cli(mocker):
    return mocker.patch('rollout.CLI')


@pytest.fixture
def mock_get_environments_list(mocker):
    return mocker.patch('rollout.get_environments_list', return_value=['ENV1'])


def test_rollout(mock_get_environments_list, mock_cli, caplog):
    rollout.rollout()

    assert caplog.records
    assert caplog.records[0].message == 'ENV1'
    assert 'Completed envs - 1' in caplog.records[-1].message


def test_rollout_failed(mock_get_environments_list, mock_cli, caplog):
    mock_cli.return_value.update.side_effect = RuntimeError('Some error')

    with pytest.raises(SystemExit):
        rollout.rollout()

    assert len(caplog.records) > 2
    assert caplog.records[0].message == 'ENV1'
    assert 'Completed envs - 0' in caplog.records[-1].message
    assert 'Failed envs - 1' in caplog.records[-2].message
