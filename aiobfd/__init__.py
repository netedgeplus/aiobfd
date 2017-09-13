"""aiobfd: Asynchronous BFD Daemon"""

import asyncio
import struct
import random

BFD_CONTROL_PORT = 3784
BFD_SOURCE_MIN = 49152
BFD_SOURCE_MAX = 65535


class Daemon:
    """Main BFD Daemon"""

    def __init__(self, local, remote, family):
        self.local = local
        self.remote = remote
        self.family = family
        self.loop = asyncio.get_event_loop()

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

    def init_control(self, remotes, rx_queue):
        """Initialize BFD Control"""
        control = Control(remotes, rx_queue)
        asyncio.ensure_future(control.run())

    def run(self):
        """Main function"""

        remotes = self.init_clients()
        rx_queue = asyncio.Queue()
        self.init_server(rx_queue)
        self.init_control(remotes, rx_queue)

        # Send a first message
        remotes[self.remote].sendto(struct.pack('hhl', 1, 2, 3),
                                    (self.remote, BFD_CONTROL_PORT))
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


class Client:
    """BFD Client for sourcing egress datagrams"""

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        """Socket setup correctly"""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Received a packet"""
        pass
        # TODO Logging, this should never happen

    @staticmethod
    def error_received(exc):
        """Error occurred"""
        # TODO Logging
        print('Error received:', exc)


class Server:
    """BFD Server for receiving ingress datagrams """

    def __init__(self, rx_queue):
        self.transport = None
        self.rx_queue = rx_queue

    def connection_made(self, transport):
        """Socket setup correctly"""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Received a packet"""
        message = data.decode()
        asyncio.ensure_future(self.rx_queue.put((message, addr[0])))
        # if source in self.peers.keys():
        #    self.peers[source].sendto(data, (source, BFD_CONTROL_PORT))

    @staticmethod
    def error_received(exc):
        """Error occurred"""
        print('Error received:', exc)


class Control:
    """BFD Control process"""

    def __init__(self, remotes, rx_queue):
        self.rx_queue = rx_queue
        self.remotes = remotes

    async def run(self):
        """Main function"""
        asyncio.ensure_future(self.rx_packet())

    async def rx_packet(self):
        """Process a received BFD Control packet"""
        while True:
            message, source = await self.rx_queue.get()
            print('Message is {} from {}'.format(message, source))
