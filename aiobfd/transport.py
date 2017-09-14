"""aiobfd: BFD IPv4/IPv6 transport"""

import asyncio


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
        # TODO Logging
        print('Error received:', exc)
