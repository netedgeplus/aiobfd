"""aiobfd: BFD Session with an individual remote"""

import struct
import asyncio
import random
from .transport import Client

SOURCE_PORT_MIN = 49152
SOURCE_PORT_MAX = 65535
CONTROL_PORT = 3784
INIT_STATE = 0
UP_STATE = 1
DOWN_STATE = 2
ADMIN_DOWN_STATE = 3


class Session:
    """BFD session with a remote"""

    def __init__(self, local, remote, family):
        self.local = local
        self.remote = remote
        self.family = family
        self.loop = asyncio.get_event_loop()

        future = self.loop.create_datagram_endpoint(
            Client,
            local_addr=(self.local,
                        random.randint(SOURCE_PORT_MIN, SOURCE_PORT_MAX)))
        self.client, _ = self.loop.run_until_complete(future)
        asyncio.ensure_future(self.tx_packets())

    async def tx_packets(self):
        """Temporary traffic source"""
        while True:
            self.client.sendto(
                struct.pack('hhl', 1, 2, 3),
                (self.remote, CONTROL_PORT)
            )
            await asyncio.sleep(0.2)
