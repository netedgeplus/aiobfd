"""Test aiobfd/control.py"""
# pylint: disable=I0011,W0621,E1101

import platform
import socket
import pytest
import aiobfd.control


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
