import asyncio
import json
import logging
import os
from random import randint

import nats
from flask import Flask
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


class WorkerStatus:
    """
    Class controls worker status
    """
    status = {'status': 'AVAILABLE'}

    def __int__(self):
        pass

    def set_busy(self) -> None:
        self.status['status'] = 'BUSY'

    def set_available(self) -> None:
        self.status['status'] = 'AVAILABLE'

    def get_status(self) -> str:
        return self.status['status']


worker_status = WorkerStatus()


class Worker:
    def __init__(self):
        self.nats_connection = None

    async def processor(self, msg: Msg) -> None:
        """
        The task should be a some simple arithmetic operation, like adding two
        numbers or subtracting two numbers. You can use time.sleep() to
        simulate long-running tasks
        :param msg: Msg
        :return: bytes
        """
        data = json.loads(msg.data.decode())
        try:
            if not data['operation'].isalpha():
                raise ValueError
            a, b, operation = float(data['a']), float(data['b']), str(data['operation'])
        except ValueError as error:
            logging.error(f"Incorrect payload: {data}, {error}")
            await self.nats_connection.publish(msg.reply, f"Incorrect payload: {data}".encode())
        else:
            worker_status.set_busy()  # worker_status.busy
            result = await self.calculator(a, b, operation)
            worker_status.set_available()  # worker_status.available
            await self.nats_connection.publish(msg.reply, str(result).encode())

    @staticmethod
    async def calculator(
            a: int | float,
            b: int | float,
            operation: str,
            delay: bool = True
    ) -> str | int | float:
        """
        operation executor wil delay operator (to accelerate test execution)
        :param delay: bool
        :param a: int | float
        :param b: int | float
        :param operation: str
        :return: str | int | float
        """
        if delay:
            await asyncio.sleep(randint(10, 30) * 0.1)  # sleep 1 - 3 sec
        if operation == WorkerOperations.add:
            return a + b
        elif operation == WorkerOperations.subtract:
            return a - b
        elif operation == WorkerOperations.multiply:
            return a * b
        elif operation == WorkerOperations.divide:
            if b == 0:
                # may be 0 division better to catch on the upper layers than here
                logging.error(f'Zero division operation provided, args: {a}, {b}, {operation}')  # noqa: E501
                return 'Zero division'
            return a / b
        else:
            error_message: str = f'Unsupported operation: `{operation}` in WORKER'
            logging.error(error_message)
            return error_message

    async def listener(self):
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
        self.nats_connection = await nats.connect(
            "nats://nats:4222",
            error_cb=error_cb,
            reconnected_cb=reconnected_cb,
            disconnected_cb=disconnected_cb,
            reconnect_time_wait=3,
            max_reconnect_attempts=-1,
        )

        while True:
            # Wait for message to come in
            await self.nats_connection.subscribe(
                subject="ops.*",
                queue="workers",
                cb=self.processor,
                pending_msgs_limit=10
            )


class WorkerService:
    def __init__(self, name):
        self.app = Flask(name)

        @self.app.route("/worker/status")
        def status():
            return {'status': str(worker_status.get_status())}

        @self.app.route("/worker/options")
        def options():
            return [i for i in WorkerOperations.__dict__.keys() if not i.startswith('_')]

    def run(self, host: str, port: int, debug: bool):
        """
        method to launch the worker service
        :param host: str
        :param port: int
        :param debug: bool
        :return:
        """
        self.app.run(host=host, port=port, debug=debug)


def main(host='0.0.0.0', port=4999, debug=True):
    service = WorkerService(__name__)
    service.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    # launch a worker
    # TODO implement run of service and worker using async
    # worker_scope = asyncio.gather(Worker().listener, main)
    # results = loop.run_until_complete(worker_scope)
    # loop.run_forever()
    asyncio.run(Worker().listener())
