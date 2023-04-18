import asyncio
import functools
import json
import logging
import os
from random import randint

import nats
from flask import Flask
from flask import request
from nats.aio.msg import Msg


class WorkerOperations:
    """
    “Add”, “Subtract”, “Multiply”, “Divide” - are available operations
    """
    add = 'add'
    subtract = 'subtract'
    multiply = 'multiply'
    divide = 'divide'


logging.basicConfig(
    filename=f'{os.path.basename(__file__).split(".")[0]}.log',
    encoding='utf-8',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logging.getLogger().addHandler(logging.StreamHandler())  # sys.stdout if not stderr needed
logging.info('Worker LOGGER initialized, ready to work')


class Server:
    def __init__(self, name):
        self.app = Flask(name)
        logging.info('Initializing worker')
        self.__available = 'AVAILABLE'
        self.__busy = 'BUSY'
        self.worker_status = self.__available
        self.operations = WorkerOperations

        @self.app.route("/worker/status")
        async def status() -> dict:
            return {'status': str(self.worker_status)}

        @self.app.route("/worker/options")
        async def options():
            return [i for i in WorkerOperations.__dict__.keys() if not i.startswith('_')]

        @self.app.route("/worker/launch")
        async def launch():
            return await self.worker()

    async def worker(self):
        """
        The worker nodes should have different properties, which indicate the
        capability of the node, for example “Add”, “Subtract”, “Multiply”, “Divide”.
        They can support all of them, some of them, or none.

         Worker nodes should be the ones connecting to the controller node. There
        should be a reconnection mechanism in case of connection failure

        The task should be a some simple arithmetic operation, like adding two
        numbers or subtracting two numbers. You can use time.sleep() to
        simulate long running tasks.
        :return:
        """

        async def error_cb(error):
            logging.error(f'NATS is unavailable, error: {error}')

        async def disconnected_cb():
            logging.warning('Lost connection to NATS, check NATS container')

        async def reconnected_cb():
            logging.info('Reconnected to NATS')

        #  Worker nodes should be the ones connecting to the controller node. There
        # should be a reconnection mechanism in case of connection failure
        nats_connection = await nats.connect(
            "nats://nats:4222",
            error_cb=error_cb,
            reconnected_cb=reconnected_cb,
            disconnected_cb=disconnected_cb,
            reconnect_time_wait=3,
            max_reconnect_attempts=-1,
        )

        @functools.lru_cache(maxsize=128)
        async def calculator(a: int | float, b: int | float, operation: str) -> str | int | float:
            """
            operation executor with cache as we can expect heavy math operation... potentially
            https://pypi.org/project/async-lru/ better to use
            :param a: int | float
            :param b: int | float
            :param operation: str
            :return: str | int | float
            """
            await asyncio.sleep(randint(50, 100) * 0.01)  # sleep 0.5 - 1 sec
            if operation == self.operations.add:
                return a + b
            elif operation == self.operations.subtract:
                return a - b
            elif operation == self.operations.multiply:
                return a * b
            elif operation == self.operations.divide:
                if b == 0:
                    # may be 0 division better to catch on the upper layers than here
                    logging.error(f'Zero division operation provided, args: {a}, {b}, {operation}')  # noqa: E501
                    return 'Zero division'
                return a / b
            else:
                error_message: str = f'Unsupported operation: `{operation}` in WORKER'
                logging.error(error_message)
                return error_message

        async def processor(msg: Msg):
            """
            The task should be a some simple arithmetic operation, like adding two
            numbers or subtracting two numbers. You can use time.sleep() to
            simulate long-running tasks
            :param msg: Msg
            :return: bytes
            """
            data = json.loads(msg.data.decode())
            a, b, operation = float(data['a']), float(data['b']), str(data['operation'])

            self.worker_status = self.__busy
            result = await calculator(a, b, operation)
            self.worker_status = self.__available
            await nats_connection.publish(msg.reply, str(result).encode())

        # while True:
        # Wait for message to come in
        while True:
            logging.info('Waiting for message to come in')
            await nats_connection.subscribe(
                subject="ops.*",
                queue="workers",
                cb=processor
            )

    def run(self, host, port, debug):
        self.app.run(host=host, port=port, debug=debug)


def main():
    server = Server(__name__)
    server.run(host='0.0.0.0', port=5002, debug=True)


if __name__ == '__main__':
    main()
