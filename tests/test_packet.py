"""Test aiobfd/packet.py"""
# pylint: disable=I0011,W0621

from copy import copy
import pytest
import bitstring
from aiobfd.packet import Packet, PACKET_FORMAT


@pytest.fixture()
def valid_data():
    """Valid sample data"""
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
    return data


def test_valid_packet(valid_data):
    """Test whether a valid packet raises no exceptions"""
    Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_protocol_version_0(valid_data):
    """Test whether packets with version 0 raise an exception"""
    data = copy(valid_data)
    data['version'] = 0
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **data), '127.0.0.1')


def test_protocol_version_2(valid_data):
    """Test whether packets with version 2 raise an exception"""
    data = copy(valid_data)
    data['version'] = 2
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **data), '127.0.0.1')
