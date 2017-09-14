"""aiobfd: BFD Control process"""

import asyncio
from .transport import Server
from .session import Session

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
            message, source = await self.rx_queue.get()
            print('Message is {} from {}'.format(message, source))

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
