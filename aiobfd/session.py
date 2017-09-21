"""aiobfd: BFD Session with an individual remote"""
# pylint: disable=I0011,R0902,R0913
# pylint: disable=I0011,E1101
# socket.IPPROTO_IPV6 missing on Windows

import asyncio
import random
import socket
import time
import logging
import bitstring
from .transport import Client
from .packet import PACKET_FORMAT, PACKET_DEBUG_MSG
log = logging.getLogger(__name__)  # pylint: disable=I0011,C0103

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

CONTROL_PLANE_INDEPENDENT = False   # Control Plane Independent

# Default timers
DESIRED_MIN_TX_INTERVAL = 1000000   # Minimum initial value

# Keep these fields statically disabled as they're not implemented
AUTH_TYPE = None                    # Authentication disabled
DEMAND_MODE = False                 # Demand Mode
MULTIPOINT = False                  # Multipoint
REQUIRED_MIN_ECHO_RX_INTERVAL = 0   # Do not support echo packet


class Session:
    """BFD session with a remote"""

    def __init__(self, local, remote, family=socket.AF_UNSPEC, passive=False,
                 tx_interval=1000000, rx_interval=1000000, detect_mult=3):
        # Argument variables
        self.local = local
        self.remote = remote
        self.family = family
        self.passive = passive
        self.loop = asyncio.get_event_loop()
        self.rx_interval = rx_interval  # User selectable value
        self.tx_interval = tx_interval  # User selectable value

        # As per 6.8.1. State Variables
        self.state = STATE_DOWN
        self.remote_state = STATE_DOWN
        self.local_discr = random.randint(0, 4294967295)  # 32-bit value
        self.remote_discr = 0
        self.local_diag = DIAG_NONE
        self._desired_min_tx_interval = DESIRED_MIN_TX_INTERVAL
        self._required_min_rx_interval = rx_interval
        self._remote_min_rx_interval = 1
        self.demand_mode = DEMAND_MODE
        self.remote_demand_mode = False
        self.detect_mult = detect_mult
        self.auth_type = AUTH_TYPE
        self.rcv_auth_seq = 0
        self.xmit_auth_seq = random.randint(0, 4294967295)  # 32-bit value
        self.auth_seq_known = False

        # State Variables beyond those defined in RFC 5880
        self._async_tx_interval = 1000000
        self._final_async_tx_interval = None  # Used to delay timer changes
        self.last_rx_packet_time = None
        self._async_detect_time = None
        self._final_async_detect_time = None  # Used to delay timer changes
        self.poll_sequence = False
        self._remote_detect_mult = None
        self._remote_min_tx_interval = None
        self._tx_packets = None

        # Create the local client and run it once to grab a port
        log.debug('Setting up UDP client for %s:%s.', remote, CONTROL_PORT)
        src_port = random.randint(SOURCE_PORT_MIN, SOURCE_PORT_MAX)
        fam, _, _, _, addr = socket.getaddrinfo(self.local, src_port)[0]
        sock = socket.socket(family=fam, type=socket.SOCK_DGRAM)
        if fam == socket.AF_INET:
            sock.setsockopt(socket.SOL_IP, socket.IP_TTL, 255)
        elif fam == socket.AF_INET6:
            # Under Windows the IPv6 socket constant is somehow missing
            # https://bugs.python.org/issue29515
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_UNICAST_HOPS, 255)
        sock.bind(addr)
        future = self.loop.create_datagram_endpoint(Client, sock=sock)
        self.client, _ = self.loop.run_until_complete(future)
        log.info('Sourcing traffic for %s:%s from %s:%s.',
                 remote, CONTROL_PORT,
                 self.client.get_extra_info('sockname')[0],
                 self.client.get_extra_info('sockname')[1])

        # Schedule the coroutines to transmit packets and detect failures
        self._tx_packets = asyncio.ensure_future(self.async_tx_packets())
        asyncio.ensure_future(self.detect_async_failure())

    # The transmit interval MUST be recalculated whenever
    # bfd.DesiredMinTxInterval changes, or whenever bfd.RemoteMinRxInterval
    # changes, and is equal to the greater of those two values.
    # If either bfd.DesiredMinTxInterval is changed or
    # bfd.RequiredMinRxInterval is changed, a Poll Sequence MUST be
    # initiated (see section 6.5)
    @property
    def desired_min_tx_interval(self):
        """bfd.DesiredMinTxInterval"""
        return self._desired_min_tx_interval

    @desired_min_tx_interval.setter
    def desired_min_tx_interval(self, value):
        if value == self._desired_min_tx_interval:
            return
        log.info('bfd.DesiredMinTxInterval changed from %d to %d, starting '
                 'Poll Sequence.', self._desired_min_tx_interval, value)

        # If bfd.DesiredMinTxInterval is increased and bfd.SessionState is Up,
        # the actual transmission interval used MUST NOT change until the Poll
        # Sequence described above has terminated.
        tx_interval = max(value, self.remote_min_rx_interval)
        if value > self._desired_min_tx_interval and self.state == STATE_UP:
            self._final_async_tx_interval = tx_interval
            log.info('Delaying increase in Tx Interval from %d to %d ...',
                     self._async_tx_interval, self._final_async_tx_interval)
        else:
            self._async_tx_interval = tx_interval
        self._desired_min_tx_interval = value
        self.poll_sequence = True

    @property
    def required_min_rx_interval(self):
        """bfd.RequiredMinRxInterval"""
        return self._required_min_rx_interval

    @required_min_rx_interval.setter
    def required_min_rx_interval(self, value):
        if value == self._required_min_rx_interval:
            return
        log.info('bfd.RequiredMinRxInterval changed from %d to %d, starting '
                 'Poll Sequence.', self._required_min_rx_interval, value)

        detect_time = self.calc_detect_time(self.remote_detect_mult,
                                            self.required_min_rx_interval,
                                            self.remote_min_tx_interval)
        if value < self._required_min_rx_interval and self.state == STATE_UP:
            self._final_async_detect_time = detect_time
            log.info('Delaying increase in Detect Time from %d to %d ...',
                     self._async_detect_time, self._final_async_detect_time)
        else:
            self._async_detect_time = detect_time
        self._required_min_rx_interval = value
        self.poll_sequence = True

    @property
    def remote_min_rx_interval(self):
        """Property for remote_min_rx_interval so we can re-calculate
            the async_tx_interval whenever this value changes"""
        return self._remote_min_rx_interval

    @remote_min_rx_interval.setter
    def remote_min_rx_interval(self, value):
        if value == self._remote_min_rx_interval:
            return
        # If the local system reduces its transmit interval due to
        # bfd.RemoteMinRxInterval being reduced (the remote system has
        # advertised a reduced value in Required Min RX Interval), and the
        # remote system is not in Demand mode, the local system MUST honor
        # the new interval immediately.
        # We should cancel the tx_packets coro to do this.
        tx_interval = max(value, self.desired_min_tx_interval)
        if tx_interval < self._async_tx_interval:
            log.info('Remote decreased the Tx Interval, forcing change '
                     'by restarting the Tx Packets process.')
            self._restart_tx_packets()
        self._remote_min_rx_interval = value

    @property
    def remote_min_tx_interval(self):
        """Property for remote_min_tx_interval so we can re-calculate
            the detect_time whenever this value changes"""
        return self._remote_min_tx_interval

    @remote_min_tx_interval.setter
    def remote_min_tx_interval(self, value):
        if value == self._remote_min_tx_interval:
            return
        self._async_detect_time = \
            self.calc_detect_time(self.remote_detect_mult,
                                  self.required_min_rx_interval, value)
        self._remote_min_tx_interval = value

    @property
    def remote_detect_mult(self):
        """Property for remote_detect_mult so we can re-calculate
            the detect_time whenever this value changes"""
        return self._remote_detect_mult

    @remote_detect_mult.setter
    def remote_detect_mult(self, value):
        if value == self._remote_detect_mult:
            return
        self._async_detect_time = \
            self.calc_detect_time(value, self.required_min_rx_interval,
                                  self.remote_min_tx_interval)
        self._remote_detect_mult = value

    @staticmethod
    def calc_detect_time(detect_mult, rx_interval, tx_interval):
        """Calculate the BFD Detection Time"""

        # In Asynchronous mode, the Detection Time calculated in the local
        # system is equal to the value of Detect Mult received from the remote
        # system, multiplied by the agreed transmit interval of the remote
        # system (the greater of bfd.RequiredMinRxInterval and the last
        # received Desired Min TX Interval).
        if not (detect_mult and rx_interval and tx_interval):
            log.debug('BFD Detection Time calculation not possible with '
                      'values detect_mult: %s rx_interval: %s tx_interval: %s',
                      detect_mult, rx_interval, tx_interval)
            return None
        log.debug('BFD Detection Time calculated using '
                  'detect_mult: %s rx_interval: %s tx_interval: %s',
                  detect_mult, rx_interval, tx_interval)
        return detect_mult * max(rx_interval, tx_interval)

    def encode_packet(self, final=False):
        """Encode a single BFD Control packet"""

        # A system MUST NOT set the Demand (D) bit unless bfd.DemandMode is 1,
        # bfd.SessionState is Up, and bfd.RemoteSessionState is Up.
        demand = (self.demand_mode and self.state == STATE_UP and
                  self.remote_state == STATE_UP)

        # A BFD Control packet MUST NOT have both the Poll (P) and Final (F)
        # bits set. We'll give the F bit priority, the P bit will still be set
        # in the next outgoing packet if needed.
        poll = self.poll_sequence if not final else False

        data = {
            'version': VERSION,
            'diag': self.local_diag,
            'state': self.state,
            'poll': poll,
            'final': final,
            'control_plane_independent': CONTROL_PLANE_INDEPENDENT,
            'authentication_present': bool(self.auth_type),
            'demand_mode': demand,
            'multipoint': MULTIPOINT,
            'detect_mult': self.detect_mult,
            'length': 24,
            'my_discr': self.local_discr,
            'your_discr': self.remote_discr,
            'desired_min_tx_interval': self.desired_min_tx_interval,
            'required_min_rx_interval': self.required_min_rx_interval,
            'required_min_echo_rx_interval': REQUIRED_MIN_ECHO_RX_INTERVAL
        }

        log.debug(PACKET_DEBUG_MSG, VERSION, self.local_diag, self.state,
                  poll, final, CONTROL_PLANE_INDEPENDENT, bool(self.auth_type),
                  demand, MULTIPOINT, self.detect_mult, 24, self.local_discr,
                  self.remote_discr, self.desired_min_tx_interval,
                  self.required_min_rx_interval, REQUIRED_MIN_ECHO_RX_INTERVAL)

        return bitstring.pack(PACKET_FORMAT, **data).bytes

    def tx_packet(self, final=False):
        """Transmit a single BFD packet to the remote peer"""
        log.debug('Sending a packet to %s:%s', self.remote, CONTROL_PORT)
        self.client.sendto(
            self.encode_packet(final), (self.remote, CONTROL_PORT))
        log.debug('Transmitting BFD packet to %s:%s.',
                  self.remote, CONTROL_PORT)

    async def async_tx_packets(self):
        """Asynchronously transmit control packet"""
        while True:
            # A system MUST NOT transmit BFD Control packets if bfd.RemoteDiscr
            # is zero and the system is taking the Passive role.
            # A system MUST NOT periodically transmit BFD Control packets if
            # bfd.RemoteMinRxInterval is zero.
            # A system MUST NOT periodically transmit BFD Control packets if
            # Demand mode is active on the remote system (bfd.RemoteDemandMode
            # is 1, bfd.SessionState is Up, and bfd.RemoteSessionState is Up)
            # and a Poll Sequence is not being transmitted.
            if not((self.remote_discr == 0 and self.passive) or
                   (self.remote_min_rx_interval == 0) or
                   (not self.poll_sequence and
                    (self.remote_demand_mode == 1 and
                     self.state == STATE_UP and
                     self.remote_state == STATE_UP))):
                self.tx_packet()

            # The periodic transmission of BFD Control packets MUST be jittered
            # on a per-packet basis by up to 25%
            # If bfd.DetectMult is equal to 1, the interval between transmitted
            # BFD Control packets MUST be no more than 90% of the negotiated
            # transmission interval, and MUST be no less than 75% of the
            # negotiated transmission interval.
            if self.detect_mult == 1:
                interval = self._async_tx_interval * random.uniform(0.75, 0.90)
            else:
                interval = self._async_tx_interval * (1 -
                                                      random.uniform(0, 0.25))
            await asyncio.sleep(interval/1000000)

    def _restart_tx_packets(self):
        """Allow other co-routines to request a restart of tx_packets()
           when needed, i.e. due to a timer change"""

        try:
            log.info('Attempting to cancel tx_packets() ...')
            self._tx_packets.cancel()
        except asyncio.CancelledError:
            pass

        log.info('tx_packets() cancelled, restarting ...')
        self._tx_packets = asyncio.ensure_future(self.async_tx_packets())

    def rx_packet(self, packet):  # pylint: disable=I0011,R0912,R0915
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
        if packet.authentication_present:
            log.critical('Authenticated packet received, not supported!')
            return

        # Set bfd.RemoteDiscr to the value of My Discriminator.
        self.remote_discr = packet.my_discr

        # Set bfd.RemoteState to the value of the State (Sta) field.
        self.remote_state = packet.state

        # Set bfd.RemoteDemandMode to the value of the Demand (D) bit.
        self.remote_demand_mode = packet.demand_mode

        # Set bfd.RemoteMinRxInterval to the value of Required Min RX Interval.
        self.remote_min_rx_interval = packet.required_min_rx_interval

        # Non-RFC defined session state that we track anyway
        self.remote_detect_mult = packet.detect_mult
        self.remote_min_tx_interval = packet.desired_min_tx_interval

        # Implmenetation of the FSM in section 6.8.6
        if self.state == STATE_ADMIN_DOWN:
            raise AttributeError('Received packet while in Admin Down state')
        if packet.state == STATE_ADMIN_DOWN:
            if self.state != STATE_DOWN:
                self.local_diag = DIAG_NEIGHBOR_SIGNAL_DOWN
                self.state = STATE_DOWN
                self.desired_min_tx_interval = DESIRED_MIN_TX_INTERVAL
                log.error('BFD remote %s signaled going ADMIN_DOWN.',
                          self.remote)
        else:
            if self.state == STATE_DOWN:
                if packet.state == STATE_DOWN:
                    self.state = STATE_INIT
                    log.error('BFD session with %s going to INIT state.',
                              self.remote)
                elif packet.state == STATE_INIT:
                    self.state = STATE_UP
                    self.desired_min_tx_interval = self.tx_interval
                    log.error('BFD session with %s going to UP state.',
                              self.remote)
            elif self.state == STATE_INIT:
                if packet.state in (STATE_INIT, STATE_UP):
                    self.state = STATE_UP
                    self.desired_min_tx_interval = self.tx_interval
                    log.error('BFD session with %s going to UP state.',
                              self.remote)
            else:
                if packet.state == STATE_DOWN:
                    self.local_diag = DIAG_NEIGHBOR_SIGNAL_DOWN
                    self.state = STATE_DOWN
                    log.error('BFD remote %s signaled going DOWN.',
                              self.remote)

        # If a BFD Control packet is received with the Poll (P) bit set to 1,
        # the receiving system MUST transmit a BFD Control packet with the Poll
        #  (P) bit clear and the Final (F) bit set as soon as practicable, ...
        if packet.poll:
            log.info('Received packet with Poll (P) bit set from %s, '
                     'sending packet with Final (F) bit set.', self.remote)
            self.tx_packet(final=True)

        # When the system sending the Poll sequence receives a packet with
        # Final, the Poll Sequence is terminated
        if packet.final:
            log.info('Received packet with Final (F) bit set from %s, '
                     'ending Poll Sequence.', self.remote)
            self.poll_sequence = False
            if self._final_async_tx_interval:
                log.info('Increasing Tx Interval from %d to %d now that Poll '
                         'Sequence has ended.', self._async_tx_interval,
                         self._final_async_tx_interval)
                self._async_tx_interval = self._final_async_tx_interval
                self._final_async_tx_interval = None
            if self._final_async_detect_time:
                log.info('Increasing Detect Time from %d to %d now that Poll '
                         'Sequence has ended.', self._async_detect_time,
                         self._final_async_detect_time)
                self._async_detect_time = self._final_async_detect_time
                self._final_async_detect_time = None

        # Set the time a packet was received to right now
        self.last_rx_packet_time = time.time()
        log.debug('Valid packet received from %s, updating last packet time.',
                  self.remote)

    async def detect_async_failure(self):
        """Detect if a session has failed in asynchronous mode"""
        while True:
            if not (self.demand_mode or self._async_detect_time is None):
                # If Demand mode is not active, and a period of time equal to
                # the Detection Time passes without receiving a BFD Control
                # packet from the remote system, and bfd.SessionState is Init
                # or Up, the session has gone down -- the local system MUST set
                # bfd.SessionState to Down and bfd.LocalDiag to 1.
                if self.state in (STATE_INIT, STATE_UP) and \
                    ((time.time() - self.last_rx_packet_time) >
                     (self._async_detect_time/1000000)):
                    self.state = STATE_DOWN
                    self.local_diag = DIAG_CONTROL_DETECTION_EXPIRED
                    self.desired_min_tx_interval = DESIRED_MIN_TX_INTERVAL
                    log.critical('Detected BFD remote %s going DOWN!',
                                 self.remote)
                    log.info('Time since last packet: %d ms; '
                             'Detect Time: %d ms',
                             (time.time() - self.last_rx_packet_time) * 1000,
                             self._async_detect_time/1000)
            await asyncio.sleep(1/1000)
