"""Test aiobfd/session.py"""
# pylint: disable=I0011,W0621,E1101,W0611

import asyncio
import platform
import socket
import pytest
import aiobfd.session


def test_session_ipv4(mocker):
    """Create a basic IPv4 Session process"""
    mocker.patch('aiobfd.session.log')
    session = aiobfd.session.Session('127.0.0.1', '127.0.0.1')
    aiobfd.session.log.debug.assert_called_once_with(
        'Setting up UDP client for %s:%s.', '127.0.0.1',
        aiobfd.session.CONTROL_PORT)
    aiobfd.session.log.info.assert_called_once_with(
        'Sourcing traffic for %s:%s from %s:%s.', '127.0.0.1',
        aiobfd.session.CONTROL_PORT, '127.0.0.1', mocker.ANY)
    try:
        session._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


@pytest.mark.skipif(platform.node() == 'carbon',
                    reason='IPv6 tests fail on Windows right now')
def test_session_ipv6(mocker):
    """Create a basic IPv6 Session process"""
    mocker.patch('aiobfd.session.log')
    session = aiobfd.session.Session('::1', '::1')
    aiobfd.session.log.debug.assert_called_once_with(
        'Setting up UDP client for %s:%s.', '::1',
        aiobfd.session.CONTROL_PORT)
    aiobfd.session.log.info.assert_called_once_with(
        'Sourcing traffic for %s:%s from %s:%s.', '::1',
        aiobfd.session.CONTROL_PORT, '::1', mocker.ANY)
    try:
        session._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


def test_session_hostname(mocker):
    """Create a basic IPv4 Session process from hostname"""
    mocker.patch('aiobfd.session.log')
    session = aiobfd.session.Session('localhost', 'localhost')
    aiobfd.session.log.debug.assert_called_once_with(
        'Setting up UDP client for %s:%s.', 'localhost',
        aiobfd.session.CONTROL_PORT)
    aiobfd.session.log.info.assert_called_once_with(
        'Sourcing traffic for %s:%s from %s:%s.', 'localhost',
        aiobfd.session.CONTROL_PORT, '127.0.0.1', mocker.ANY)
    try:
        session._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


def test_session_host_force_ipv4(mocker):
    """Create a forced IPv4 Session process from hostname"""
    mocker.patch('aiobfd.session.log')
    session = aiobfd.session.Session('localhost', 'localhost',
                                     family=socket.AF_INET)
    aiobfd.session.log.debug.assert_called_once_with(
        'Setting up UDP client for %s:%s.', 'localhost',
        aiobfd.session.CONTROL_PORT)
    aiobfd.session.log.info.assert_called_once_with(
        'Sourcing traffic for %s:%s from %s:%s.', 'localhost',
        aiobfd.session.CONTROL_PORT, '127.0.0.1', mocker.ANY)
    try:
        session._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass


@pytest.mark.skipif(platform.node() == 'carbon',
                    reason='IPv6 tests fail on Windows right now')
def test_session_host_force_ipv6(mocker):
    """Create a forced IPv6 Session process from hostname"""
    mocker.patch('aiobfd.session.log')
    session = aiobfd.session.Session('localhost', 'localhost',
                                     family=socket.AF_INET6)
    aiobfd.session.log.debug.assert_called_once_with(
        'Setting up UDP client for %s:%s.', 'localhost',
        aiobfd.session.CONTROL_PORT)
    aiobfd.session.log.info.assert_called_once_with(
        'Sourcing traffic for %s:%s from %s:%s.', 'localhost',
        aiobfd.session.CONTROL_PORT, '::1', mocker.ANY)
    try:
        session._tx_packets.cancel()  # pylint: disable=I0011,W0212
    except asyncio.CancelledError:
        pass
