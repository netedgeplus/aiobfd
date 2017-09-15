"""aiobfd: BFD Control process"""

import asyncio
import logging
from .transport import Server
from .session import Session
from .packet import Packet

CONTROL_PORT = 3784


class Control:
    """BFD Control"""

    def __init__(self, local, remotes, family):
        self.loop = asyncio.get_event_loop()
        self.rx_queue = asyncio.Queue()

        # Initialize client sessions
        self.sessions = list()
        for remote in remotes:
            self.sessions.append(Session(local, remote, family))

        # Initialize server
        future = self.loop.create_datagram_endpoint(
            lambda: Server(self.rx_queue),
            local_addr=(local, CONTROL_PORT))
        self.server, _ = self.loop.run_until_complete(future)

    async def rx_packets(self):
        """Process a received BFD Control packets"""
        while True:
            packet, source = await self.rx_queue.get()
            asyncio.ensure_future(self.process_packet(packet, source))
            self.rx_queue.task_done()

    async def process_packet(self, data, source):
        """Process a received packet"""
        try:
            packet = Packet(data, source)
        except IOError as exc:
            logging.debug('Dropping packet: %s', exc)
            return

        # If the Your Discriminator field is nonzero, it MUST be used to select
        # the session with which this BFD packet is associated.  If no session
        # is found, the packet MUST be discarded.
        if packet.your_disc:
            for session in self.sessions:
                if session.local_discr == packet.your_disc:
                    session.rx_packet(packet)
                    break
        else:
            # If the Your Discriminator field is zero, the session MUST be
            # selected based on some combination of other fields ...
            for session in self.sessions:
                if session.remote == packet.source:
                    session.rx_packet(packet, True)
                    break

        # If a matching session is not found, a new session MAY be created,
        # or the packet MAY be discarded.
        logging.debug('Dropping packet from %s as it doesn\'t match any '
                      'session.', packet.source)

    def run(self):
        """Main function"""

        asyncio.ensure_future(self.rx_packets())

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            def shutdown_exception_handler(loop, context):
                """Do not show `asyncio.CancelledError` exceptions"""
                if "exception" not in context or not \
                   isinstance(context["exception"], asyncio.CancelledError):
                    loop.default_exception_handler(context)
            self.loop.set_exception_handler(shutdown_exception_handler)

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
