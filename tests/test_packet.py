"""Test aiobfd/packet.py"""
# pylint: disable=I0011,W0621

import pytest
import bitstring
from aiobfd.packet import Packet, PACKET_FORMAT

PACKET_FORMAT_TOO_SHORT = (
    'uint:3=version,'
    'uint:5=diag,'
    'uint:2=state,'
    'bool=poll,'
    'bool=final,'
    'bool=control_plane_independent,'
    'bool=authentication_present,'
    'bool=demand_mode,'
    'bool=multipoint,'
    'uint:8=detect_mult,'
    'uint:8=length,'
)


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


def test_packet_too_short(valid_data):
    """Test whether version 0 raises an exception"""
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT_TOO_SHORT, **valid_data),
               '127.0.0.1')


def test_protocol_version_0(valid_data):
    """Test whether version 0 raises an exception"""
    valid_data['version'] = 0
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_protocol_version_2(valid_data):
    """Test whether version 2 raises an exception"""
    valid_data['version'] = 2
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_length_23(valid_data):
    """Test whether too short length raises an exception"""
    valid_data['length'] = 23
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_length_0(valid_data):
    """Test whether no length set raises an exception"""
    valid_data['length'] = 0
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_length_25(valid_data):
    """Test whether length beyond packet size raises exception"""
    valid_data['length'] = 25
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_multipoint(valid_data):
    """Test whether setting the multipoint bit raises an exception"""
    valid_data['multipoint'] = 1
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_my_discr_0(valid_data):
    """Test whether leaving the my_discr empty raises an exception"""
    valid_data['my_discr'] = 0
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_your_discr_0_when_up(valid_data):
    """Test whether your_disc being 0 when in up state raises an exception """
    valid_data['state'] = 3
    valid_data['your_discr'] = 0
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')


def test_your_discr_0_when_init(valid_data):
    """Test whether your_disc being 0 when in init state raises an
       exception """
    valid_data['state'] = 2
    valid_data['your_discr'] = 0
    with pytest.raises(IOError):
        Packet(bitstring.pack(PACKET_FORMAT, **valid_data), '127.0.0.1')
