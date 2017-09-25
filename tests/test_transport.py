"""Test aiobfd/transport.py"""
# pylint: disable=I0011,W0621,E1101

import pytest
import aiobfd.transport


@pytest.fixture(scope='session')
def client():
    """Create an aoibfd client"""
    return aiobfd.transport.Client()


def test_client_connection_made(client):
    """Test whether we can establish client connections"""
    client.connection_made(None)


def test_client_datagram_received(client, mocker):
    """Test whether we can establish client connections"""
    mocker.patch('aiobfd.transport.log')
    client.datagram_received('data', ('127.0.0.1', 12345))
    aiobfd.transport.log.info.assert_called_once_with(
        'Unexpectedly received a packet on a BFD source port from %s on port '
        '%d', '127.0.0.1', 12345)


def test_client_error_received(client, mocker):
    """Test whether we can establish client connections"""
    mocker.patch('aiobfd.transport.log')
    client.error_received('test error')
    aiobfd.transport.log.error.assert_called_once_with(
        'Socket error received: %s', 'test error')
