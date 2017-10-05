"""aiobfd: BFD Control process"""
# pylint: disable=I0011,R0913

import asyncio
import logging
import socket
from .transport import Server
from .session import Session
from .packet import Packet
log = logging.getLogger(__name__)  # pylint: disable=I0011,C0103

CONTROL_PORT = 3784


class Control:
    """BFD Control"""

    def __init__(self, local, remotes, family=socket.AF_UNSPEC, passive=False,
                 tx_interval=1000000, rx_interval=1000000, detect_mult=3,
                 loop=asyncio.get_event_loop()):
        self.loop = loop
        self.rx_queue = asyncio.Queue()

        # Initialize client sessions
        self.sessions = list()
        for remote in remotes:
            log.debug('Creating BFD session for remote %s.', remote)
            self.sessions.append(
                Session(local, remote, family=family, passive=passive,
                        tx_interval=tx_interval, rx_interval=rx_interval,
                        detect_mult=detect_mult))

        # Initialize server
        log.debug('Setting up UDP server on %s:%s.', local, CONTROL_PORT)
        task = self.loop.create_datagram_endpoint(
            lambda: Server(self.rx_queue),
            local_addr=(local, CONTROL_PORT),
            family=family)
        self.server, _ = self.loop.run_until_complete(task)
        log.info('Accepting traffic on %s:%s.',
                 self.server.get_extra_info('sockname')[0],
                 self.server.get_extra_info('sockname')[1])

    async def rx_packets(self):
        """Process a received BFD Control packets"""
        log.debug('Control process ready to receive packets.')
        while True:
            packet, source = await self.rx_queue.get()
            log.debug('Received a new packet from %s.', source)
            self.process_packet(packet, source)
            self.rx_queue.task_done()

    def process_packet(self, data, source):
        """Process a received packet"""
        try:
            packet = Packet(data, source)
        except IOError as exc:
            log.info('Dropping packet: %s', exc)
            return

        # If the Your Discriminator field is nonzero, it MUST be used to select
        # the session with which this BFD packet is associated.  If no session
        # is found, the packet MUST be discarded.
        if packet.your_discr:
            for session in self.sessions:
                if session.local_discr == packet.your_discr:
                    session.rx_packet(packet)
                    return
        else:
            # If the Your Discriminator field is zero, the session MUST be
            # selected based on some combination of other fields ...
            for session in self.sessions:
                if session.remote == packet.source:
                    session.rx_packet(packet)
                    return

        # If a matching session is not found, a new session MAY be created,
        # or the packet MAY be discarded. Note: We discard for now.
        log.info('Dropping packet from %s as it doesn\'t match any '
                 'configured remote.', packet.source)

    def run(self):
        """Main function"""

        asyncio.ensure_future(self.rx_packets())

        try:
            log.warning('BFD Daemon fully configured.')
            self.loop.run_forever()
        except KeyboardInterrupt:
            def shutdown_exception_handler(loop, context):
                """Do not show `asyncio.CancelledError` exceptions"""
                if "exception" not in context or not \
                   isinstance(context["exception"], asyncio.CancelledError):
                    loop.default_exception_handler(context)
            self.loop.set_exception_handler(shutdown_exception_handler)
            log.info('Keyboard interrupt detected.')

            # Wait for all tasks to be cancelled
            tasks = asyncio.gather(*asyncio.Task.all_tasks(loop=self.loop),
                                   loop=self.loop, return_exceptions=True)
            tasks.add_done_callback(lambda t: self.loop.stop())
            tasks.cancel()

            # Keep the event loop running until it is either destroyed or all
            # tasks have really terminated
            while not tasks.done() and not self.loop.is_closed():
                self.loop.run_forever()
        finally:
            self.loop.close()
