"""Test aiobfd/session.py"""
# pylint: disable=I0011,W0621,E1101,W0611,W0212

import asyncio
import platform
import socket
import time
from unittest.mock import MagicMock
import bitstring
import pytest
import aiobfd.session
from aiobfd.packet import Packet, PACKET_FORMAT


class AsyncMock(MagicMock):
    """Make MagicMock Async"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


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
def session():
    """Create a basic aiobfd session"""
    return aiobfd.session.Session('127.0.0.1', '127.0.0.1')


@pytest.fixture()
def valid_packet():
    """Valid sample packet"""
    data = {
        'version': 1,
        'diag': 0,
        'state': 0,
        'poll': 0,
        'final': 0,
        'control_plane_independent': 0,
        'authentication_present': 0,
        'demand_mode': 0,
        'multipoint': 0,
        'detect_mult': 1,
        'length': 24,
        'my_discr': 1,
        'your_discr': 0,
        'desired_min_tx_interval': 50000,
        'required_min_rx_interval': 50000,
        'required_min_echo_rx_interval': 0
    }
    return Packet(bitstring.pack(PACKET_FORMAT, **data), '127.0.0.1')


def test_session_ipv4(mocker):
    """Create a basic IPv4 Session process"""
    mocker.patch('aiobfd.session.log')
    mocker.patch.object(aiobfd.session.Session, 'async_tx_packets',
                        new_callable=AsyncMock)
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
    mocker.patch.object(aiobfd.session.Session, 'async_tx_packets',
                        new_callable=AsyncMock)
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
    mocker.patch.object(aiobfd.session.Session, 'async_tx_packets',
                        new_callable=AsyncMock)
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
    mocker.patch.object(aiobfd.session.Session, 'async_tx_packets',
                        new_callable=AsyncMock)
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
    mocker.patch.object(aiobfd.session.Session, 'async_tx_packets',
                        new_callable=AsyncMock)
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


def test_sess_r_tx_interval_get(session):
    """Attempt to get the Remote Min Tx Interval"""
    assert session._remote_min_tx_interval is None


def test_sess_r_tx_int_set_same(session, mocker):
    """Attempt to set the Remote Min Tx Interval to same value"""
    session.remote_min_tx_interval = 1000000
    mocker.patch('aiobfd.session.log')
    session.remote_min_tx_interval = 1000000
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_min_tx_interval == 1000000


def test_sess_r_tx_int_set_diff1(session, mocker):
    """Attempt to set the Remote Min Tx Interval to different value"""
    mocker.patch('aiobfd.session.log')
    session.remote_min_tx_interval = 1000000
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_min_tx_interval == 1000000
    assert session._async_detect_time is None


def test_sess_r_tx_int_set_diff2(session, mocker):
    """Attempt to set the Remote Min Tx Interval to different value"""
    session.remote_detect_mult = 2
    mocker.patch('aiobfd.session.log')
    session.remote_min_tx_interval = 1000000
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_min_tx_interval == 1000000
    assert session._async_detect_time == 2000000


def test_sess_r_detect_mult_get(session):
    """Attempt to get the Remote Detect Multiplier"""
    assert session._remote_detect_mult is None


def test_sess_r_det_mult_set_same(session, mocker):
    """Attempt to set the Remote Detect Multiplier to same value"""
    session.remote_detect_mult = 2
    mocker.patch('aiobfd.session.log')
    session.remote_detect_mult = 2
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_detect_mult == 2


def test_sess_r_det_mult_set_same1(session, mocker):
    """Attempt to set the Remote Detect Multiplier to different value"""
    mocker.patch('aiobfd.session.log')
    session.remote_detect_mult = 2
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_detect_mult == 2
    assert session._async_detect_time is None


def test_sess_r_det_mult_set_same2(session, mocker):
    """Attempt to set the Remote Detect Multiplier to different value"""
    session.remote_min_tx_interval = 1000000
    mocker.patch('aiobfd.session.log')
    session.remote_detect_mult = 2
    aiobfd.session.log.info.assert_not_called()
    assert session._remote_detect_mult == 2
    assert session._async_detect_time == 2000000


def test_sess_detect_time_normal1(session, mocker):
    """Calculate the detect time standard case"""
    mocker.patch('aiobfd.session.log')
    result = session.calc_detect_time(3, 100, 200)
    assert result == 600
    aiobfd.session.log.debug.assert_called_once_with(
        'BFD Detection Time calculated using '
        'detect_mult: %s rx_interval: %s tx_interval: %s',
        3, 100, 200)


def test_sess_detect_time_normal2(session, mocker):
    """Calculate the detect time standard case"""
    mocker.patch('aiobfd.session.log')
    result = session.calc_detect_time(3, 200, 100)
    assert result == 600
    aiobfd.session.log.debug.assert_called_once_with(
        'BFD Detection Time calculated using '
        'detect_mult: %s rx_interval: %s tx_interval: %s',
        3, 200, 100)


def test_sess_detect_time_none1(session, mocker):
    """Calculate the detect time standard case"""
    mocker.patch('aiobfd.session.log')
    result = session.calc_detect_time(None, 100, 200)
    assert result is None
    aiobfd.session.log.debug.assert_called_once_with(
        'BFD Detection Time calculation not possible with '
        'values detect_mult: %s rx_interval: %s tx_interval: %s',
        None, 100, 200)


def test_sess_detect_time_none2(session, mocker):
    """Calculate the detect time standard case"""
    mocker.patch('aiobfd.session.log')
    result = session.calc_detect_time(3, None, 200)
    assert result is None
    aiobfd.session.log.debug.assert_called_once_with(
        'BFD Detection Time calculation not possible with '
        'values detect_mult: %s rx_interval: %s tx_interval: %s',
        3, None, 200)


def test_sess_detect_time_none3(session, mocker):
    """Calculate the detect time standard case"""
    mocker.patch('aiobfd.session.log')
    result = session.calc_detect_time(3, 100, None)
    assert result is None
    aiobfd.session.log.debug.assert_called_once_with(
        'BFD Detection Time calculation not possible with '
        'values detect_mult: %s rx_interval: %s tx_interval: %s',
        3, 100, None)


@pytest.mark.asyncio  # noqa: F811
async def test_async_tx_pkts_mult_1(session, mocker):
    """Test the async detect internval with multiplier 1"""
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(0)
    mocker.patch('aiobfd.session.log')
    session.detect_mult = 1
    with pytest.raises(CallableExhausted):
        await session.async_tx_packets()
    asyncio.sleep.assert_called_once_with(mocker.ANY)


@pytest.mark.asyncio  # noqa: F811
async def test_async_tx_pkts_mult_2(session, mocker):
    """Test the async detect internval with multiplier 2"""
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(0)
    mocker.patch('aiobfd.session.log')
    session.detect_mult = 2
    with pytest.raises(CallableExhausted):
        await session.async_tx_packets()
    asyncio.sleep.assert_called_once_with(mocker.ANY)


@pytest.mark.asyncio  # noqa: F811
async def test_async_tx_pkt_passive1(session, mocker):
    """Test whether we send packets when the session is passive"""
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(0)
    mocker.patch.object(session, 'tx_packet')
    session.passive = True
    with pytest.raises(CallableExhausted):
        await session.async_tx_packets()
    session.tx_packet.assert_not_called()


@pytest.mark.asyncio  # noqa: F811
async def test_async_tx_pkt_passive2(session, mocker):
    """Test whether we send packets when passive but remote discr known"""
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(0)
    mocker.patch.object(session, 'tx_packet')
    session.passive = True
    session.remote_discr = 22
    with pytest.raises(CallableExhausted):
        await session.async_tx_packets()
    session.tx_packet.assert_called_once_with()


@pytest.mark.asyncio  # noqa: F811
async def test_async_tx_pkt_rem_rx_0(session, mocker):
    """Test whether we send packets when the remote Rx Interval is 0"""
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(0)
    mocker.patch.object(session, 'tx_packet')
    session.remote_min_rx_interval = 0
    with pytest.raises(CallableExhausted):
        await session.async_tx_packets()
    session.tx_packet.assert_not_called()


@pytest.mark.asyncio  # noqa: F811
async def test_async_tx_pkt_demand1(session, mocker):
    """Test whether we send packets when the remote is in demand mode"""
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(0)
    mocker.patch.object(session, 'tx_packet')
    session.remote_demand_mode = True
    session.state = aiobfd.session.STATE_UP
    session.remote_state = aiobfd.session.STATE_UP
    with pytest.raises(CallableExhausted):
        await session.async_tx_packets()
    session.tx_packet.assert_not_called()


@pytest.mark.asyncio  # noqa: F811
async def test_async_tx_pkt_demand2(session, mocker):
    """Test whether we send packets when the remote is in demand mode and we
       have initiated a poll sequence."""
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(0)
    mocker.patch.object(session, 'tx_packet')
    session.remote_demand_mode = True
    session.state = aiobfd.session.STATE_UP
    session.remote_state = aiobfd.session.STATE_UP
    session.poll_sequence = True
    with pytest.raises(CallableExhausted):
        await session.async_tx_packets()
    session.tx_packet.assert_called_once_with()


def test_tx_packet(session, mocker):
    """Test whether tx_packet() sends packets to client"""
    mocker.patch('aiobfd.session.log')
    mocker.patch.object(session, 'encode_packet')
    mocker.patch.object(session, 'client')
    session.encode_packet.return_value = 'under_test'
    session.tx_packet()
    session.encode_packet.assert_called_once_with(False)
    session.client.sendto.assert_called_once_with(
        mocker.ANY, ('127.0.0.1', aiobfd.session.CONTROL_PORT))
    aiobfd.session.log.debug.assert_called_once_with(
        'Transmitting BFD packet to %s:%s', '127.0.0.1',
        aiobfd.session.CONTROL_PORT)


def test_restart_tx_packets(session, mocker):
    """Test the restart_tx_packet() procedure"""
    mocker.patch('aiobfd.session.log')
    session._restart_tx_packets()
    aiobfd.session.log.info.assert_has_calls(
        [mocker.call('Attempting to cancel tx_packets() ...'),
         mocker.call('Restarting tx_packets()  ...')])


@pytest.mark.asyncio  # noqa: F811
async def test_detect_down(session, mocker):
    """Test the detection logic, really down"""
    session.required_min_rx_interval = 4000
    session.remote_detect_mult = 3
    session.remote_min_tx_interval = 2000
    session.last_rx_packet_time = time.time()
    session.state = aiobfd.session.STATE_UP
    await asyncio.sleep(((3 * 4000) + 1000)/1000000)
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(1)
    mocker.patch('aiobfd.session.log')
    with pytest.raises(CallableExhausted):
        await session.detect_async_failure()
    assert session.state == aiobfd.session.STATE_DOWN
    assert session.local_diag == aiobfd.session.DIAG_CONTROL_DETECTION_EXPIRED
    assert session.desired_min_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL
    aiobfd.session.log.critical.assert_called_once_with(
        'Detected BFD remote %s going DOWN!', '127.0.0.1')
    aiobfd.session.log.info.assert_called_once_with(
        'Time since last packet: %d ms; Detect Time: %d ms',
        mocker.ANY, ((3 * 4000))/1000)


@pytest.mark.asyncio  # noqa: F811
async def test_detect_up(session, mocker):
    """Test the detection logic, still up"""
    session.required_min_rx_interval = 4000
    session.remote_detect_mult = 3
    session.remote_min_tx_interval = 2000
    session.last_rx_packet_time = time.time()
    session.state = aiobfd.session.STATE_UP
    await asyncio.sleep(((4000))/1000000)
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(1)
    mocker.patch('aiobfd.session.log')
    with pytest.raises(CallableExhausted):
        await session.detect_async_failure()
    aiobfd.session.log.critical.assert_not_called()
    aiobfd.session.log.info.assert_not_called()


@pytest.mark.asyncio  # noqa: F811
async def test_detect_demand_mode(session, mocker):
    """Test the detection logic, in demand mode"""
    session.required_min_rx_interval = 4000
    session.remote_detect_mult = 3
    session.remote_min_tx_interval = 2000
    session.last_rx_packet_time = time.time()
    session.state = aiobfd.session.STATE_UP
    session.demand_mode = True
    await asyncio.sleep(((3 * 4000) + 1000)/1000000)
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(1)
    mocker.patch('aiobfd.session.log')
    with pytest.raises(CallableExhausted):
        await session.detect_async_failure()
    aiobfd.session.log.critical.assert_not_called()
    aiobfd.session.log.info.assert_not_called()


@pytest.mark.asyncio  # noqa: F811
async def test_detect_no_detect_time(session, mocker):
    """Test the detection logic, no detect_time set"""
    session.required_min_rx_interval = 4000
    session.remote_detect_mult = 3
    session.remote_min_tx_interval = 2000
    session.last_rx_packet_time = time.time()
    session.state = aiobfd.session.STATE_UP
    session._async_detect_time = None
    await asyncio.sleep(((3 * 4000) + 1000)/1000000)
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(1)
    mocker.patch('aiobfd.session.log')
    with pytest.raises(CallableExhausted):
        await session.detect_async_failure()
    aiobfd.session.log.critical.assert_not_called()
    aiobfd.session.log.info.assert_not_called()


@pytest.mark.asyncio  # noqa: F811
async def test_detect_state_init(session, mocker):
    """Test the detection logic, in init state"""
    session.required_min_rx_interval = 4000
    session.remote_detect_mult = 3
    session.remote_min_tx_interval = 2000
    session.last_rx_packet_time = time.time()
    session.state = aiobfd.session.STATE_INIT
    await asyncio.sleep(((3 * 4000) + 1000)/1000000)
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(1)
    mocker.patch('aiobfd.session.log')
    with pytest.raises(CallableExhausted):
        await session.detect_async_failure()
    assert session.state == aiobfd.session.STATE_DOWN
    assert session.local_diag == aiobfd.session.DIAG_CONTROL_DETECTION_EXPIRED
    assert session.desired_min_tx_interval == \
        aiobfd.session.DESIRED_MIN_TX_INTERVAL
    aiobfd.session.log.critical.assert_called_once_with(
        'Detected BFD remote %s going DOWN!', '127.0.0.1')
    aiobfd.session.log.info.assert_called_once_with(
        'Time since last packet: %d ms; Detect Time: %d ms',
        mocker.ANY, ((3 * 4000))/1000)


@pytest.mark.asyncio  # noqa: F811
async def test_detect_state_admin_down(session, mocker):
    """Test the detection logic, in admin down state"""
    session.required_min_rx_interval = 4000
    session.remote_detect_mult = 3
    session.remote_min_tx_interval = 2000
    session.last_rx_packet_time = time.time()
    session.state = aiobfd.session.STATE_ADMIN_DOWN
    await asyncio.sleep(((3 * 4000) + 1000)/1000000)
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(1)
    mocker.patch('aiobfd.session.log')
    with pytest.raises(CallableExhausted):
        await session.detect_async_failure()
    aiobfd.session.log.critical.assert_not_called()
    aiobfd.session.log.info.assert_not_called()


@pytest.mark.asyncio  # noqa: F811
async def test_detect_state_down(session, mocker):
    """Test the detection logic, in down state"""
    session.required_min_rx_interval = 4000
    session.remote_detect_mult = 3
    session.remote_min_tx_interval = 2000
    session.last_rx_packet_time = time.time()
    session.state = aiobfd.session.STATE_DOWN
    await asyncio.sleep(((3 * 4000) + 1000)/1000000)
    mocker.patch.object(asyncio, 'sleep',
                        new_callable=AsyncMock)
    asyncio.sleep.side_effect = ErrorAfter(1)
    mocker.patch('aiobfd.session.log')
    with pytest.raises(CallableExhausted):
        await session.detect_async_failure()
    aiobfd.session.log.critical.assert_not_called()
    aiobfd.session.log.info.assert_not_called()


def test_rx_packet_auth_bit(session, valid_packet, mocker):
    """Test whether A bit is set while we are not configured for auth"""
    mocker.patch('aiobfd.session.log')
    valid_packet.authentication_present = True
    with pytest.raises(IOError) as excinfo:
        session.rx_packet(valid_packet)
    assert 'Received packet with authentication while no '\
           'authentication is configured locally.' in str(excinfo.value)


def test_rx_packet_auth_sess(session, valid_packet, mocker):
    """Test whether A bit is unset while we are configured for auth"""
    mocker.patch('aiobfd.session.log')
    session.auth_type = 1
    with pytest.raises(IOError) as excinfo:
        session.rx_packet(valid_packet)
    assert 'Received packet without authentication while '\
           'authentication is configured locally.' in str(excinfo.value)


def test_rx_packet_auth_both(session, valid_packet, mocker):
    """Authentication configured but not implemented !?"""
    mocker.patch('aiobfd.session.log')
    session.auth_type = 1
    valid_packet.authentication_present = True
    session.rx_packet(valid_packet)
    aiobfd.session.log.critical.assert_called_once_with(
        'Authenticated packet received, not supported!')


def test_rx_packet_remote_update(session, valid_packet, mocker):
    """Check whether we store all info from the remote"""
    mocker.patch('aiobfd.session.log')
    valid_packet.my_discr = 12345
    valid_packet.state = 2
    session.rx_packet(valid_packet)
    assert session.remote_discr == 12345
    assert session.remote_state == 2
    assert session.remote_demand_mode == 0
    assert session.remote_min_rx_interval == 50000
    assert session.remote_detect_mult == 1
    assert session.remote_min_tx_interval == 50000
    assert session.last_rx_packet_time is not None
    aiobfd.session.log.debug.assert_has_calls(
        [mocker.call(
            'Valid packet received from %s, updating last packet time.',
            '127.0.0.1')])


def test_rx_packet_poll(session, valid_packet, mocker):
    """Check whether the P bit is acted on"""
    mocker.patch('aiobfd.session.log')
    mocker.patch.object(session, 'tx_packet')
    valid_packet.poll = True
    session.rx_packet(valid_packet)
    session.tx_packet.assert_called_once_with(final=True)
    aiobfd.session.log.info.assert_called_once_with(
        'Received packet with Poll (P) bit set from %s, '
        'sending packet with Final (F) bit set.', '127.0.0.1')


def test_rx_packet_final(session, valid_packet, mocker):
    """Check whether the F bit is acted on"""
    mocker.patch('aiobfd.session.log')
    valid_packet.final = True
    session.poll_sequence = True
    session.rx_packet(valid_packet)
    assert session.poll_sequence is False
    aiobfd.session.log.info.assert_called_once_with(
        'Received packet with Final (F) bit set from %s, '
        'ending Poll Sequence.', '127.0.0.1')


def test_rx_pkt_final_tx_interval(session, valid_packet, mocker):
    """Check whether the final async tx interval is applied"""
    mocker.patch('aiobfd.session.log')
    valid_packet.final = True
    session.poll_sequence = True
    session._final_async_tx_interval = 123000
    session.rx_packet(valid_packet)
    assert session.poll_sequence is False
    aiobfd.session.log.info.assert_has_calls(
        [mocker.call('Increasing Tx Interval from %d to %d now that Poll '
                     'Sequence has ended.', 1000000, 123000)])
    assert session._async_tx_interval == 123000
    assert session._final_async_tx_interval is None


def test_rx_pkt_final_detect_time(session, valid_packet, mocker):
    """Check whether the final async detect time is applied"""
    mocker.patch('aiobfd.session.log')
    valid_packet.final = True
    session.poll_sequence = True
    session._final_async_detect_time = 123000
    session.rx_packet(valid_packet)
    assert session.poll_sequence is False
    aiobfd.session.log.info.assert_has_calls(
        [mocker.call('Increasing Detect Time from %d to %d now that Poll '
                     'Sequence has ended.', 1000000, 123000)])
    assert session._async_detect_time == 123000
    assert session._final_async_detect_time is None


def test_rx_pkt_fsm_this_admin_down(session, valid_packet, mocker):
    """Check whether the FSM on Rx Packet works in admin down"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_ADMIN_DOWN
    session.rx_packet(valid_packet)
    aiobfd.session.log.warning.assert_called_once_with(
        'Received packet from %s while in Admin Down state.', '127.0.0.1')


def test_rx_pkt_fsm_admin_down(session, valid_packet, mocker):
    """Check whether the FSM on Rx Packet with admin down"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_UP
    valid_packet.state = aiobfd.session.STATE_ADMIN_DOWN
    session.rx_packet(valid_packet)
    aiobfd.session.log.error.assert_called_once_with(
        'BFD remote %s signaled going ADMIN_DOWN.', '127.0.0.1')
    assert session.local_diag == aiobfd.session.DIAG_NEIGHBOR_SIGNAL_DOWN
    assert session.state == aiobfd.session.STATE_DOWN


def test_rx_pkt_fsm_down(session, valid_packet, mocker):
    """Check whether the FSM on Rx Packet with down"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_UP
    valid_packet.state = aiobfd.session.STATE_DOWN
    session.rx_packet(valid_packet)
    aiobfd.session.log.error.assert_called_once_with(
        'BFD remote %s signaled going DOWN.', '127.0.0.1')
    assert session.local_diag == aiobfd.session.DIAG_NEIGHBOR_SIGNAL_DOWN
    assert session.state == aiobfd.session.STATE_DOWN


def test_rx_pkt_fsm_down_down(session, valid_packet, mocker):
    """Check whether the FSM on Rx Packet with local & remote down"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_DOWN
    valid_packet.state = aiobfd.session.STATE_DOWN
    session.rx_packet(valid_packet)
    aiobfd.session.log.error.assert_called_once_with(
        'BFD session with %s going to INIT state.', '127.0.0.1')
    assert session.state == aiobfd.session.STATE_INIT


def test_rx_pkt_fsm_down_init(session, valid_packet, mocker):
    """Check whether the FSM on Rx Packet with local down & remote down"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_DOWN
    session.tx_interval = 5000
    valid_packet.state = aiobfd.session.STATE_INIT
    session.rx_packet(valid_packet)
    aiobfd.session.log.error.assert_called_once_with(
        'BFD session with %s going to UP state.', '127.0.0.1')
    assert session.state == aiobfd.session.STATE_UP
    assert session.desired_min_tx_interval == 5000


def test_rx_pkt_fsm_init_init(session, valid_packet, mocker):
    """Check whether the FSM on Rx Packet with local & remote init"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_INIT
    session.tx_interval = 5000
    valid_packet.state = aiobfd.session.STATE_INIT
    session.rx_packet(valid_packet)
    aiobfd.session.log.error.assert_called_once_with(
        'BFD session with %s going to UP state.', '127.0.0.1')
    assert session.state == aiobfd.session.STATE_UP
    assert session.desired_min_tx_interval == 5000


def test_rx_pkt_fsm_init_up(session, valid_packet, mocker):
    """Check whether the FSM on Rx Packet with local init & remote up"""
    mocker.patch('aiobfd.session.log')
    session.state = aiobfd.session.STATE_INIT
    session.tx_interval = 5000
    valid_packet.state = aiobfd.session.STATE_UP
    session.rx_packet(valid_packet)
    aiobfd.session.log.error.assert_called_once_with(
        'BFD session with %s going to UP state.', '127.0.0.1')
    assert session.state == aiobfd.session.STATE_UP
    assert session.desired_min_tx_interval == 5000
