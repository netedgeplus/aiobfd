"""aiobfd: BFD Session with an individual remote"""
# pylint: disable=I0011,R0902

import asyncio
import random
import socket
import bitstring
from .transport import Client
from .packet import PACKET_FORMAT

SOURCE_PORT_MIN = 49152
SOURCE_PORT_MAX = 65535
CONTROL_PORT = 3784

VERSION = 1

DIAG_NONE = 0                       # No Diagnostic
DIAG_CONTROL_DETECTION_EXPIRED = 1  # Control Detection Time Expired
DIAG_ECHO_FAILED = 2                # Echo Function Failed
DIAG_NEIGHBOR_SIGNAL_DOWN = 3       # Neighbor Signaled Session Down
DIAG_FORWARD_PLANE_RESET = 4        # Forwarding Plane Reset
DIAG_PATH_DOWN = 5                  # Path Down
DIAG_CONCAT_PATH_DOWN = 6           # Concatenated Path Down
DIAG_ADMIN_DOWN = 7                 # Administratively Down
DIAG_REV_CONCAT_PATH_DOWN = 8       # Reverse Concatenated Path Down

STATE_ADMIN_DOWN = 0                # AdminDown
STATE_DOWN = 1                      # Down
STATE_INIT = 2                      # Init
STATE_UP = 3                        # Up

CONTROL_PLANE_INDEPENDENT = False  # Control Plane Independent

# Default timers
DESIRED_MIN_TX_INTERVAL = 1         # Minimum initial value
REQUIRED_MIN_RX_INTERVAL = 1        # TODO: parameterize
DETECT_MULT = 3                     # TODO: paramiterize

# Keep these fields statically disabled as they're not implemented
AUTH_TYPE = None                    # Authentication disabled
DEMAND_MODE = False                 # Demand Mode
MULTIPOINT = False                  # Multipoint
REQUIRED_MIN_ECHO_RX_INTERVAL = 0   # Do not support echo packet


class Session:
    """BFD session with a remote"""

    def __init__(self, local, remote, family=socket.AF_UNSPEC, passive=False):
        self.local = local
        self.remote = remote
        self.family = family
        self.passive = passive
        self.loop = asyncio.get_event_loop()

        self.state = STATE_DOWN
        self.remote_state = STATE_DOWN
        self.local_discr = random.randint(0, 4294967295)  # 32-bit value
        self.remote_disc = 0
        self.local_diag = DIAG_NONE
        self.desired_min_tx_interval = DESIRED_MIN_TX_INTERVAL
        self.required_min_rx_interval = REQUIRED_MIN_RX_INTERVAL
        self.remote_min_rx_interval = 1
        self.demand_mode = DEMAND_MODE
        self.remote_demand_mode = False
        self.detect_mult = DETECT_MULT
        self.auth_type = AUTH_TYPE
        self.rcv_auth_seq = 0
        self.xmit_auth_seq = random.randint(0, 4294967295)  # 32-bit value
        self.auth_seq_known = False

        future = self.loop.create_datagram_endpoint(
            Client,
            local_addr=(self.local,
                        random.randint(SOURCE_PORT_MIN, SOURCE_PORT_MAX)))
        self.client, _ = self.loop.run_until_complete(future)
        asyncio.ensure_future(self.tx_packets())

    def encode_packet(self, poll=False, final=False):
        """Encode a single BFD Control packet"""

        # A system MUST NOT set the Demand (D) bit unless bfd.DemandMode is 1,
        # bfd.SessionState is Up, and bfd.RemoteSessionState is Up.
        demand_bit = (self.demand_mode and self.state == STATE_UP and
                      self.remote_state == STATE_UP)

        data = {
            'version': VERSION,
            'diag': self.local_diag,
            'state': self.state,
            'poll': poll,
            'final': final,
            'control_plane_independent': CONTROL_PLANE_INDEPENDENT,
            'authentication_present': bool(self.auth_type),
            'demand_mode': demand_bit,
            'multipoint': MULTIPOINT,
            'detect_mult': self.detect_mult,
            'length': 24,  # TODO: revisit when implementing authentication
            'my_disc': self.local_discr,
            'your_disc': self.remote_disc,
            'desired_min_tx_interval': self.desired_min_tx_interval,
            'required_min_rx_interval': self.required_min_rx_interval,
            'required_min_echo_rx_interval': REQUIRED_MIN_ECHO_RX_INTERVAL
        }

        return bitstring.pack(PACKET_FORMAT, **data).bytes

    def tx_packet(self, poll=False, final=False):
        """Transmit a single BFD packet to the remote peer"""
        self.client.sendto(
            self.encode_packet(poll, final), (self.remote, CONTROL_PORT))

    async def tx_packets(self):
        """Temporary traffic source"""
        while True:

            # A system MUST NOT transmit BFD Control packets if bfd.RemoteDiscr
            # is zero and the system is taking the Passive role.
            # A system MUST NOT periodically transmit BFD Control packets if
            # bfd.RemoteMinRxInterval is zero.
            # A system MUST NOT periodically transmit BFD Control packets if
            # Demand mode is active on the remote system (bfd.RemoteDemandMode
            # is 1, bfd.SessionState is Up, and bfd.RemoteSessionState is Up)
            # and a Poll Sequence is not being transmitted.
            # TODO:  6.8.7. ... and a Poll Sequence is not being transmitted.
            print(self.passive)
            if not((self.remote_disc == 0 and self.passive) or
                   (self.remote_min_rx_interval == 0) or
                   (self.remote_demand_mode == 1 and self.state == STATE_UP and
                    self.remote_state == STATE_UP)):
                print('Sending packet')
                self.tx_packet()

            # A system MUST NOT transmit BFD Control packets at an interval
            # less than the larger of bfd.DesiredMinTxInterval and
            # bfd.RemoteMinRxInterval less applied jitter (see below).
            interval = max([self.desired_min_tx_interval,
                            self.remote_min_rx_interval])

            # The periodic transmission of BFD Control packets MUST be jittered
            # on a per-packet basis by up to 25%
            # If bfd.DetectMult is equal to 1, the interval between transmitted
            # BFD Control packets MUST be no more than 90% of the negotiated
            # transmission interval, and MUST be no less than 75% of the
            # negotiated transmission interval.
            if self.detect_mult == 1:
                interval *= random.uniform(0.75, 0.90)
            else:
                interval *= (1 - random.uniform(0, 0.25))

            print('Tx interval is {}'.format(interval))
            await asyncio.sleep(interval)
            # TODO: Implement 6.8.7.  Transmitting BFD Control Packets

    def rx_packet(self, packet):  # pylint: disable=I0011,R0912
        """Receive packet"""

        # If the A bit is set and no authentication is in use (bfd.AuthType
        # is zero), the packet MUST be discarded.
        if packet.authentication_present and not self.auth_type:
            raise IOError('Received packet with authentication while no '
                          'authentication is configured locally.')

        # If the A bit is clear and authentication is in use (bfd.AuthType
        # is nonzero), the packet MUST be discarded.
        if (not packet.authentication_present) and self.auth_type:
            raise IOError('Received packet without authentication while '
                          'authentication is configured locally.')

        # If the A bit is set authenticate the packet under the rules of
        # section 6.7.
        # TODO: implement authentication
        if packet.authentication_present:
            pass

        # Set bfd.RemoteDiscr to the value of My Discriminator.
        self.remote_disc = packet.my_disc

        # Set bfd.RemoteState to the value of the State (Sta) field.
        self.remote_state = packet.state

        # Set bfd.RemoteDemandMode to the value of the Demand (D) bit.
        self.remote_demand_mode = packet.demand_mode

        # Set bfd.RemoteMinRxInterval to the value of Required Min RX Interval.
        self.remote_min_rx_interval = packet.required_min_rx_interval

        # Implmenetation of the FSM in section 6.8.6
        # TODO: log session state changes
        if self.state == STATE_ADMIN_DOWN:
            raise RuntimeWarning('Received packet while in Admin Down state')
        if packet.state == STATE_ADMIN_DOWN:
            if self.state != STATE_DOWN:
                self.local_diag = DIAG_NEIGHBOR_SIGNAL_DOWN
                self.state = STATE_DOWN
        else:
            if self.state == STATE_DOWN:
                if packet.state == STATE_DOWN:
                    self.state = STATE_INIT
                elif packet.state == STATE_INIT:
                    self.state = STATE_UP
            elif self.state == STATE_INIT:
                if packet.state in (STATE_INIT, STATE_UP):
                    self.state = STATE_UP
            else:
                if packet.state == STATE_DOWN:
                    self.local_diag = DIAG_NEIGHBOR_SIGNAL_DOWN
                    self.state = STATE_DOWN

        # TODO: Check to see if Demand mode should become active or not
        # (section 6.8.6 end of paragraph)(see section 6.6).

        # If a BFD Control packet is received with the Poll (P) bit set to 1,
        # the receiving system MUST transmit a BFD Control packet with the Poll
        #  (P) bit clear and the Final (F) bit set as soon as practicable, ...
        if packet.poll:
            self.tx_packet(final=True)

        # TODO: implement timer resets here and detect missing packet
