"""aiobfd: BFD Control process"""

import asyncio
import struct
import random
from .transport import Client, Server

BFD_CONTROL_PORT = 3784
BFD_SOURCE_MIN = 49152
BFD_SOURCE_MAX = 65535


class Control:
    """BFD Control"""

    def __init__(self, local, remote, family):
        self.local = local
        self.remote = remote
        self.family = family
        self.loop = asyncio.get_event_loop()
        self.rx_queue = rx_queue = asyncio.Queue()
        self.remotes = self.init_clients()
        self.init_server(rx_queue)

    def init_clients(self):
        """Initialize client(s)"""

        client_coro = self.loop.create_datagram_endpoint(
            Client,
            local_addr=(self.local,
                        random.randint(BFD_SOURCE_MIN, BFD_SOURCE_MAX)))
        client, _ = self.loop.run_until_complete(client_coro)
        return {self.remote: client}

    def init_server(self, rx_queue):
        """Initialize server"""

        server_coro = self.loop.create_datagram_endpoint(
            lambda: Server(rx_queue),
            local_addr=(self.local, BFD_CONTROL_PORT))
        self.loop.run_until_complete(server_coro)

    async def rx_packet(self):
        """Process a received BFD Control packet"""
        while True:
            message, source = await self.rx_queue.get()
            print('Message is {} from {}'.format(message, source))

    async def tx_packet(self):
        """Temporary traffic source"""
        while True:
            self.remotes[self.remote].sendto(
                struct.pack('hhl', 1, 2, 3),
                (self.remote, BFD_CONTROL_PORT))
            await asyncio.sleep(0.5)

    def run(self):
        """Main function"""

        asyncio.ensure_future(self.rx_packet())
        asyncio.ensure_future(self.tx_packet())

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
