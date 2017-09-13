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

    def run(self):
        """Main function"""

        loop = asyncio.get_event_loop()
        print("Starting UDP server")

        client_coro = loop.create_datagram_endpoint(
            Client,
            local_addr=(self.local,
                        random.randint(BFD_SOURCE_MIN, BFD_SOURCE_MAX)))
        client, _ = loop.run_until_complete(client_coro)

        peers = {self.remote: client}

        server_coro = loop.create_datagram_endpoint(
            lambda: Server(peers),
            local_addr=(self.local, BFD_CONTROL_PORT))
        server, _ = loop.run_until_complete(server_coro)

        client.sendto(struct.pack('hhl', 1, 2, 3),
                      (self.remote, BFD_CONTROL_PORT))
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        client.close()
        server.close()
        loop.close()


class Client:
    """BFD Client for sourcing egress datagrams"""

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        """Socket setup correctly"""
        self.transport = transport

    def error_received(self, exc):
        """Error occurred"""
        print('Error received:', exc)


class Server:
    """BFD Server for receiving ingress datagrams """

    def __init__(self, peers):
        self.transport = None
        self.peers = peers

    def connection_made(self, transport):
        """Socket setup correctly"""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Received a packet"""
        message = data.decode()
        print('Received %r from %s' % (message, addr))
        source = addr[0]
        if source in self.peers.keys():
            self.peers[source].sendto(data, (source, BFD_CONTROL_PORT))

    def error_received(self, exc):
        """Error occurred"""
        print('Error received:', exc)
