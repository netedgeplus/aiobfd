"""Test aiobfd/session.py"""
# pylint: disable=I0011,W0621,E1101,W0611,W0212

import asyncio
import platform
import socket
from unittest.mock import MagicMock
import pytest
import aiobfd.session


@pytest.fixture()
def session():
    """Create a basic aiobfd session"""
    return aiobfd.session.Session('127.0.0.1', '127.0.0.1')


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
        session._tx_packets.cancel()
    except asyncio.CancelledError:
        pass


def test_sess_tx_interval_get(session):
    """Attempt to get the Desired Min Tx Interval"""
    assert session.desired_min_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL


def test_sess_tx_interval_set_same(session, mocker):
    """Attempt to set the Desired Min Tx Interval to same value"""
    mocker.patch('aiobfd.session.log')
    session.desired_min_tx_interval = aiobfd.session.DESIRED_MIN_TX_INTERVAL
    aiobfd.session.log.info.assert_not_called()


def test_sess_tx_interval_set_less(session, mocker):
    """Attempt to set the Desired Min Tx Interval to lower value"""
    mocker.patch('aiobfd.session.log')
    session.desired_min_tx_interval = \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL - 1
    aiobfd.session.log.info.assert_called_once_with(
        'bfd.DesiredMinTxInterval changed from %d to %d, starting '
        'Poll Sequence.', aiobfd.session.DESIRED_MIN_TX_INTERVAL,
        aiobfd.session.DESIRED_MIN_TX_INTERVAL - 1)
    assert session._async_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL - 1
    assert session._desired_min_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL - 1
    assert session.poll_sequence


def test_sess_tx_interval_set_more(session, mocker):
    """Attempt to set the Desired Min Tx Interval to higher value"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_UP
    session.desired_min_tx_interval = \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL + 1
    aiobfd.session.log.info.assert_has_calls(
        [mocker.call(
            'bfd.DesiredMinTxInterval changed from %d to %d, starting '
            'Poll Sequence.', aiobfd.session.DESIRED_MIN_TX_INTERVAL,
            aiobfd.session.DESIRED_MIN_TX_INTERVAL + 1),
         mocker.call('Delaying increase in Tx Interval from %d to %d ...',
                     aiobfd.session.DESIRED_MIN_TX_INTERVAL,
                     aiobfd.session.DESIRED_MIN_TX_INTERVAL + 1)])
    assert session._async_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL
    assert session._final_async_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL + 1
    assert session._desired_min_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL + 1
    assert session.poll_sequence


def test_sess_rx_interval_get(session):
    """Attempt to get the Required Min Rx Interval"""
    assert session.required_min_rx_interval == 1000000


def test_sess_rx_interval_set_same(session, mocker):
    """Attempt to set the Required Min Rx Interval to same value"""
    mocker.patch('aiobfd.session.log')
    session.required_min_rx_interval = 1000000
    aiobfd.session.log.info.assert_not_called()


def test_sess_rx_interval_set_less(session, mocker):
    """Attempt to set the Required Min Rx Interval to lower value"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_UP
    session._remote_min_tx_interval = 900000
    session.remote_detect_mult = 3
    session.required_min_rx_interval = 1000000 - 1
    aiobfd.session.log.info.assert_has_calls(
        [mocker.call(
            'bfd.RequiredMinRxInterval changed from %d to %d, starting '
            'Poll Sequence.', 1000000, 1000000 - 1),
         mocker.call('Delaying decrease in Detect Time from %d to %d ...',
                     1000000 * 3, (1000000 - 1) * 3)])
    assert session._async_detect_time == (1000000) * 3
    assert session._final_async_detect_time == (1000000 - 1) * 3
    assert session._required_min_rx_interval == 1000000 - 1
    assert session.poll_sequence


def test_sess_rx_interval_set_more(session, mocker):
    """Attempt to set the Required Min Rx Interval to higher value"""
    mocker.patch('aiobfd.session.log')
    session._remote_min_tx_interval = 900000
    session.remote_detect_mult = 3
    session.required_min_rx_interval = 1000000 + 1
    aiobfd.session.log.info.assert_called_once_with(
        'bfd.RequiredMinRxInterval changed from %d to %d, starting '
        'Poll Sequence.', 1000000, 1000000 + 1)
    assert session._async_detect_time == (1000000 + 1) * 3
    assert session._required_min_rx_interval == 1000000 + 1
    assert session.poll_sequence


def test_sess_r_rx_interval_get(session):
    """Attempt to get the Remote Min Rx Interval"""
    assert session._remote_min_rx_interval == 1


def test_sess_r_rx_int_set_same(session, mocker):
    """Attempt to set the Remote Min Rx Interval to same value"""
    mocker.patch('aiobfd.session.log')
    session.remote_min_rx_interval = 1
    aiobfd.session.log.info.assert_not_called()


def test_sess_r_rx_int_set_diff(session, mocker):
    """Attempt to set the Remote Min Rx Interval to different value"""
    mocker.patch('aiobfd.session.log')
    session.remote_min_rx_interval = 1000000
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_min_rx_interval == 1000000


def test_sess_r_rx_int_set_diff1(session, mocker):
    """Attempt to set the Remote Min Rx Interval to different value
       but lower than our DESIRED_MIN_TX_INTERVAL"""
    mocker.patch('aiobfd.session.log')
    session.remote_min_rx_interval = 900000
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_min_rx_interval == 900000
    assert session._async_tx_interval == 1000000


def test_sess_r_rx_int_set_diff2(session, mocker):
    """Attempt to set the Remote Min Rx Interval to different value
       but higher than our DESIRED_MIN_TX_INTERVAL"""
    mocker.patch('aiobfd.session.log')
    session.remote_min_rx_interval = 1100000
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_min_rx_interval == 1100000
    assert session._async_tx_interval == 1100000


def test_sess_r_rx_int_set_diff3(session, mocker):
    """Attempt to set the Remote Min Rx Interval to different value
       such that the Tx Interval decreases"""

    session.remote_min_rx_interval = 1500000
    mocker.patch('aiobfd.session.log')
    session._restart_tx_packets = MagicMock()
    session.remote_min_rx_interval = 900000
    aiobfd.session.log.info.assert_called_once_with(
        'Remote triggered decrease in the Tx Interval, forcing '
        'change by restarting the Tx Packets process.')
    assert session._restart_tx_packets.called
    assert session._remote_min_rx_interval == 900000
    assert session._async_tx_interval == 1000000
