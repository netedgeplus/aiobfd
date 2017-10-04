"""Test aiobfd/control.py"""
# pylint: disable=I0011,W0621,E1101,W0611

import platform
import socket
from unittest.mock import MagicMock
import asyncio
import pytest
import bitstring
import aiobfd.control
from aiobfd.packet import PACKET_FORMAT
from tests.test_packet import PACKET_FORMAT_TOO_SHORT
from tests.test_packet import valid_data  # noqa: F401


class ErrorAfter(object):  # pylint: disable=I0011,R0903
    """ Callable that will raise `CallableExhausted`
    exception after `limit` calls """
    def __init__(self, limit):
        self.limit = limit
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls > self.limit:
            raise CallableExhausted


class CallableExhausted(Exception):
    """Exception that gets raised after `limit` calls"""
    pass


@pytest.fixture()
def control(event_loop):
    """Create a basic aiobfd control session"""
    return aiobfd.control.Control('127.0.0.1', ['127.0.0.1'], loop=event_loop)


def test_control_ipv4(mocker):
    """Create a basic IPv4 Control process"""
    mocker.patch('aiobfd.control.log')
    aiobfd.control.Control('127.0.0.1', ['127.0.0.1'])
    aiobfd.control.log.debug.assert_has_calls(
        [mocker.call('Creating BFD session for remote %s.', '127.0.0.1'),
         mocker.call('Setting up UDP server on %s:%s.', '127.0.0.1',
                     aiobfd.control.CONTROL_PORT)])
    aiobfd.control.log.info.assert_called_once_with(
        'Accepting traffic on %s:%s.', '127.0.0.1',
        aiobfd.control.CONTROL_PORT)


@pytest.mark.skipif(platform.node() == 'carbon',
                    reason='IPv6 tests fail on Windows right now')
def test_control_ipv6(mocker):
    """Create a basic IPv6 Control process"""
    mocker.patch('aiobfd.control.log')
    aiobfd.control.Control('::1', ['::1'])
    aiobfd.control.log.debug.assert_has_calls(
        [mocker.call('Creating BFD session for remote %s.', '::1'),
         mocker.call('Setting up UDP server on %s:%s.', '::1',
                     aiobfd.control.CONTROL_PORT)])
    aiobfd.control.log.info.assert_called_once_with(
        'Accepting traffic on %s:%s.', '::1',
        aiobfd.control.CONTROL_PORT)


def test_control_hostname(mocker):
    """Create a basic IPv4 Control process from hostname"""
    mocker.patch('aiobfd.control.log')
    aiobfd.control.Control('localhost', ['localhost'])
    aiobfd.control.log.debug.assert_has_calls(
        [mocker.call('Creating BFD session for remote %s.', 'localhost'),
         mocker.call('Setting up UDP server on %s:%s.', 'localhost',
                     aiobfd.control.CONTROL_PORT)])
    aiobfd.control.log.info.assert_called_once_with(
        'Accepting traffic on %s:%s.', '127.0.0.1',
        aiobfd.control.CONTROL_PORT)


def test_control_hostname_force_v4(mocker):
    """Create a forced IPv4 Control process from hostname"""
    mocker.patch('aiobfd.control.log')
    aiobfd.control.Control('localhost', ['localhost'], family=socket.AF_INET)
    aiobfd.control.log.debug.assert_has_calls(
        [mocker.call('Creating BFD session for remote %s.', 'localhost'),
         mocker.call('Setting up UDP server on %s:%s.', 'localhost',
                     aiobfd.control.CONTROL_PORT)])
    aiobfd.control.log.info.assert_called_once_with(
        'Accepting traffic on %s:%s.', '127.0.0.1',
        aiobfd.control.CONTROL_PORT)


@pytest.mark.skipif(platform.node() == 'carbon',
                    reason='IPv6 tests fail on Windows right now')
def test_control_hostname_force_v6(mocker):
    """Create a forced IPv6 Control process from hostname"""
    mocker.patch('aiobfd.control.log')
    aiobfd.control.Control('localhost', ['localhost'], family=socket.AF_INET6)
    aiobfd.control.log.debug.assert_has_calls(
        [mocker.call('Creating BFD session for remote %s.', 'localhost'),
         mocker.call('Setting up UDP server on %s:%s.', 'localhost',
                     aiobfd.control.CONTROL_PORT)])
    aiobfd.control.log.info.assert_called_once_with(
        'Accepting traffic on %s:%s.', '::1',
        aiobfd.control.CONTROL_PORT)


def test_process_invalid_packet(control, valid_data, mocker):  # noqa: F811
    """Inject an invalid packet and monitor the log"""
    packet = bitstring.pack(PACKET_FORMAT_TOO_SHORT, **valid_data)
    mocker.patch('aiobfd.control.log')
    control.process_packet(packet, '172.0.0.1')
    aiobfd.control.log.info.assert_called_once_with(
        'Dropping packet: %s', mocker.ANY)
    try:
        control.sessions[0]._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


def test_process_pkt_unknown_remote(control, valid_data, mocker):  # noqa: F811
    """Inject a valid packet from unconfigured remote and monitor the log"""
    packet = bitstring.pack(PACKET_FORMAT, **valid_data)
    mocker.patch('aiobfd.control.log')
    control.process_packet(packet, '127.0.0.2')
    aiobfd.control.log.info.assert_called_once_with(
        'Dropping packet from %s as it doesn\'t match any configured remote.',
        '127.0.0.2')
    try:
        control.sessions[0]._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


def test_valid_remote_your_discr_0(control, valid_data, mocker):  # noqa: F811
    """Inject a valid packet and monitor the log"""
    packet = bitstring.pack(PACKET_FORMAT, **valid_data)
    mocker.patch('aiobfd.control.log')
    control.process_packet(packet, '127.0.0.1')
    aiobfd.control.log.info.assert_not_called()
    aiobfd.control.log.warning.assert_not_called()
    aiobfd.control.log.debug.assert_not_called()
    try:
        control.sessions[0]._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


def test_valid_remote_your_discr_1(control, valid_data, mocker):  # noqa: F811
    """Inject a valid packet and monitor the log"""
    valid_data['your_discr'] = control.sessions[0].local_discr
    packet = bitstring.pack(PACKET_FORMAT, **valid_data)
    mocker.patch('aiobfd.control.log')
    control.process_packet(packet, '127.0.0.1')
    aiobfd.control.log.info.assert_not_called()
    aiobfd.control.log.warning.assert_not_called()
    aiobfd.control.log.debug.assert_not_called()
    try:
        control.sessions[0]._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio  # noqa: F811
async def test_rx_packets(control, valid_data):
    """Test the Rx Packets loop"""
    control.process_packet = MagicMock(side_effect=ErrorAfter(1))
    await control.rx_queue.put((valid_data, '127.0.0.1'))
    await control.rx_queue.put((valid_data, '127.0.0.1'))
    with pytest.raises(CallableExhausted):
        await control.rx_packets()
