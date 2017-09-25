"""Test aiobfd/transport.py"""
# pylint: disable=I0011,W0621,E1101

import asyncio
import pytest
import aiobfd.transport


@pytest.fixture(scope='session')
def client():
    """Create an aoibfd client"""
    return aiobfd.transport.Client()


@pytest.fixture(scope='session')
def server():
    """Create an aoibfd server"""
    rx_queue = asyncio.Queue()
    return aiobfd.transport.Server(rx_queue)


def test_client_connection_made(client):
    """Test whether we can establish client connections"""
    client.connection_made(None)


def test_client_datagram_received(client, mocker):
    """Test whether receiving packets on a client port creates a log entry"""
    mocker.patch('aiobfd.transport.log')
    client.datagram_received('data', ('127.0.0.1', 12345))
    aiobfd.transport.log.info.assert_called_once_with(
        'Unexpectedly received a packet on a BFD source port from %s on port '
        '%d', '127.0.0.1', 12345)


def test_client_error_received(client, mocker):
    """Test whether receiving errors on a client creates a log entry"""
    mocker.patch('aiobfd.transport.log')
    client.error_received('test error')
    aiobfd.transport.log.error.assert_called_once_with(
        'Socket error received: %s', 'test error')


def test_server_connection_made(server, mocker):
    """Test whether we can establish a server connections"""
    mocker.patch(server.rx_queue)
    server.connection_made(None)


def test_server_datagram_received(server):
    """Test whether receiving packets on the server queues them"""
    server.datagram_received('data', ('127.0.0.1', 12345))


def test_server_error_received(server, mocker):
    """Test whether receiving errors on a server creates a log entry"""
    mocker.patch('aiobfd.transport.log')
    server.error_received('test error')
    aiobfd.transport.log.error.assert_called_once_with(
        'Socket error received: %s', 'test error')
