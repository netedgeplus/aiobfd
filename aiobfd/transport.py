"""aiobfd: BFD IPv4/IPv6 transport"""

import asyncio
import logging

class Client:
    """BFD Client for sourcing egress datagrams"""

    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        """Socket setup correctly"""
        self.transport = transport

    @staticmethod
    def datagram_received(_, addr):
        """Received a packet"""
        logging.error(('Unexpectedly received a packet on a BFD source port '
                       'from %s on port %d'), addr[0], addr[1])

    @staticmethod
    def error_received(exc):
        """Error occurred"""
        logging.warning('Socket error received: %s', exc)


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
        asyncio.ensure_future(self.rx_queue.put((data, addr[0])))

    @staticmethod
    def error_received(exc):
        """Error occurred"""
        logging.warning('Socket error received: %s', exc)
