"""aiobfd: BFD Session with an individual remote"""
# pylint: disable=I0011,R0902

import asyncio
import random
import bitstring
from .transport import Client
from .packet import PACKET_FORMAT

SOURCE_PORT_MIN = 49152
SOURCE_PORT_MAX = 65535
CONTROL_PORT = 3784

VERSION = 1

DIAG_NONE = 0                       # No Diagnostic
DIAG_ = 1                           # Control Detection Time Expired
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
DETECT_MULT = 5                     # TODO: paramiterize

# Keep these fields statically disabled as they're not implemented
AUTH_TYPE = None                    # Authentication disabled
DEMAND_MODE = False                 # Demand Mode
MULTIPOINT = False                  # Multipoint
REQUIRED_MIN_ECHO_RX_INTERVAL = 0   # Do not support echo packet


class Session:
    """BFD session with a remote"""

    def __init__(self, local, remote, family):
        self.local = local
        self.remote = remote
        self.family = family
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
        data = {
            'version': VERSION,
            'diag': self.local_diag,
            'state': self.state,
            'poll': poll,
            'final': final,
            'control_plane_independent': CONTROL_PLANE_INDEPENDENT,
            'authentication_present': bool(self.auth_type),
            'demand_mode': self.demand_mode,
            'multipoint': MULTIPOINT,
            'detect_mult': self.detect_mult,
            'length': 24,
            'my_disc': self.local_discr,
            'your_disc': self.remote_disc,
            'desired_min_tx_interval': self.desired_min_tx_interval,
            'required_min_rx_interval': self.required_min_rx_interval,
            'required_min_echo_rx_interval': REQUIRED_MIN_ECHO_RX_INTERVAL
        }

        return bitstring.pack(PACKET_FORMAT, **data).bytes

    async def tx_packets(self):
        """Temporary traffic source"""
        while True:
            self.client.sendto(
                self.encode_packet(), (self.remote, CONTROL_PORT))
            await asyncio.sleep(0.2)
