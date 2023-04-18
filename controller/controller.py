import asyncio
import json
import logging
import os
from datetime import datetime

import nats
from flask import Flask, request, jsonify, abort, Response
from nats.aio.msg import Msg
from nats.errors import TimeoutError


class TaskStatus:
    """
    available statuses for provided tasks
    """
    queued = 'QUEUED'
    running = 'RUNNING'
    done = 'DONE'
    failed = 'FAILED'


class WorkerOperations:
    """
    “Add”, “Subtract”, “Multiply”, “Divide”
    """
    add = 'add'
    subtract = 'substract'
    multiply = 'multiply'
    divide = 'divide'


class TaskStorage:
    def __init__(self):
        """
        set some data structure to handle tasks
        """
        self.tasks = {}
        # TODO protobuf expected
        self.fields = ['a', 'b', 'operation', 'status', 'uid']

    def task_add(self, data: dict) -> bool | str:
        """
        store new tasks in storage
        :param data: dict
        :return: bool
        """
        if all([i in data for i in self.fields]):
            if data['uid'] not in self.tasks:
                # set default stats
                data['status'] = TaskStatus.queued
                # add new task to storage
                self.tasks.update({data['uid']: data})
                return True
            return False
        else:
            logging.error(f'Wrong payload structure. Expected fields: `{self.fields}` got `{data}`')  # noqa: E501
            return 'Error: data structure is incorrect'

    def task_update_status(self, uid: str, status: str) -> bool:
        if uid in self.tasks:
            self.tasks[uid]['status'] = status
            return True
        return False

    def task_get_status(self, uid: str) -> str | bool:
        """

        :param uid:
        :return:
        """
        if uid in self.tasks:
            return self.tasks[uid]['status']
        return False


logging.basicConfig(
    filename=f'{os.path.basename(__file__).split(".")[0]}.log',
    encoding='utf-8',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logging.getLogger().addHandler(logging.StreamHandler())
logging.info('Controller LOGGER initialized, ready to work')

# task in-memory storage
storage = TaskStorage()


class Controller:
    """
    Back-end service also in OOP style :)
    """

    def __init__(self, name):
        self.app = Flask(name)

        @self.app.route('/controller/options', methods=['GET'])
        def options():
            return [i for i in WorkerOperations.__dict__.keys() if not i.startswith('_')]  # noqa: E501

        @self.app.route('/task/status', methods=['GET'])
        def get_task_stats() -> Response:
            """
            get task status by UID
            :param task_uid: str
            :return:
            """
            logging.info(f'GET req status: {request.args}, {request}')
            args = request.args
            task_uid = args.get('uid')  # /<int:task_uid>
            if not storage.task_get_status(task_uid):
                abort(404, f"NO UID: {task_uid} in storage")
            return jsonify({'task_status': storage.task_get_status(task_uid)})

        @self.app.route('/operator', methods=['POST'])
        async def operator() -> bytes:
            """
            general operator for actions
            :return: bytes
            """

            form: dict = json.loads(request.json)
            logging.info(f"Incoming req: {form}")
            if request.method == 'POST':
                return await self.task_handler(form)
            else:
                return 'NON-POST are not processed'.encode()

    @staticmethod
    def arg_check(value: str) -> bool:
        """
        Check args are numeric to avoid error
        :param value: str
        :return: bool
        """
        try:
            float(value)
            return True
        except ValueError:
            return False

    async def task_processor(self, task: dict, timeout=10) -> bytes:
        """
        Process task and set statuses after running
        :param task: dict
        :param timeout: int
        :return: bytes
        """

        async def error_cb(error):
            logging.error(f'NATS is unavailable, check NATS container, error: {error}')  # noqa: E501

        async def disconnected_cb():
            logging.error('Lost connection to NATS, check NATS container')

        async def reconnected_cb():
            logging.info('Reconnected to NATS')

        # check args on the back-end
        if not self.arg_check(task["a"]) or not self.arg_check(task["b"]):
            logging.error(f'wrong arg type provided to controller')
            return f'wrong arg type: `{type(task["a"])}`, `{type(task["b"])}`, expected INT or FLOAT'.encode()  # noqa: E501
        # check operation on te back-end
        logging.info(f"form type: {type(task)}, payload: {task}")
        if task['operation'] in [
            option for option in WorkerOperations.__dict__.keys()
            if not option.startswith('_')
        ]:

            #  Worker nodes should be the ones connecting to the controller node. There
            # should be a reconnection mechanism in case of connection failure
            nats_connection = await nats.connect(
                "nats://nats:4222",
                error_cb=error_cb,
                reconnected_cb=reconnected_cb,
                disconnected_cb=disconnected_cb,
                reconnect_time_wait=1,
                max_reconnect_attempts=-1
            )

            logging.info(f"Task: {str(task)}")
            subject_name: str = f"ops.{task['operation']}"
            started = datetime.now()
            try:
                """
                There should be some timeout for each task. For example if task1 has a 
                timeout of 10 seconds, it should be completed before that, otherwise the 
                task can be considered as “FAILED”.
                """

                response: Msg = await nats_connection.request(
                    subject=subject_name,
                    # TODO protobuf expected
                    payload=json.dumps(task).encode(),
                    timeout=timeout
                )
                finished = datetime.now()
                logging.info(f"Request time execution: = {finished - started}")

                log_msg: str = f"Controller received response: {response.data.decode()}"  # noqa: E501
                logging.info(log_msg)
                storage.task_update_status(task['uid'], TaskStatus.done)
                return response.data
            except TimeoutError as error:
                finished = datetime.now()
                logging.info(f"Request time execution: = {finished - started}")
                storage.task_update_status(task['uid'], TaskStatus.failed)
                err_msg: str = 'Request timed out'
                logging.error(f"{err_msg}: {error}")
                return err_msg.encode()
            except Exception as error:
                finished = datetime.now()
                logging.info(f"Request time execution: = {finished - started}")
                storage.task_update_status(task['uid'], TaskStatus.failed)
                logging.error(f"All other unexpected problems: {error}")  # noqa: E501
                return f"Unknown problem, check {os.path.basename(__file__).split('.')[0]}.log file".encode()  # noqa: E501

        else:
            storage.task_update_status(task['uid'], TaskStatus.failed)
            return f"Unsupported operation: `{task['operation']}` check -help for proper options".encode()  # noqa: E501

    async def task_handler(self, task) -> bytes:
        """
        Handle task status and give a callback for existing one
        :param task: dict
        :return: bytes
        """
        if task['uid'] not in storage.tasks:
            task['status'] = TaskStatus.queued
            storage.task_add(task)
            return await self.task_processor(task)
        else:
            return storage.task_get_status(task['uid']).encode()

    def run(self, host: str, port: int, debug: bool):
        """
        method to launch the back-end service
        :param host: str
        :param port: int
        :param debug: bool
        :return:
        """
        self.app.run(host=host, port=port, debug=debug)


def main(host='0.0.0.0', port=5000, debug=True):
    service = Controller(__name__)
    service.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()