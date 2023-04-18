import argparse
import asyncio
import functools
import json
import logging
import os
import uuid

import aiohttp
from flask import Flask, request, render_template

logging.basicConfig(
    filename=f'{os.path.basename(__file__).split(".")[0]}.log',
    encoding='utf-8',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logging.getLogger().addHandler(logging.StreamHandler())  # sys.stdout if not stderr needed


class TaskStatus:
    """
    available statuses for provided tasks
    """
    queued = 'QUEUED'
    running = 'RUNNING'
    done = 'DONE'
    failed = 'FAILED'


async def post(url: str, payload: dict, timeout: int = 12) -> bytes:
    """
    Simple POST executor for JSON payload with
    :param timeout: int in seconds 12 seconds by default
    :param url: str
    :param payload: dict
    :return: bytes
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
                url=url,
                headers={'Content-type': 'application/json'},
                json=json.dumps(payload),
                timeout=timeout
        ) as response:
            return await response.content.read()


class FrontEnd:
    """
    front-end service in OOP style :)
    """

    def __init__(self, name, html_folder: str = 'pages'):
        """

        :param name: str
        :param html_folder: str setup HTML folder
        """
        # TODO - template_folder='pages' should be dynamical or from config
        self.app = Flask(name, template_folder=html_folder)

        @self.app.route('/')
        @self.app.route('/index')
        def view_form():
            return render_template('main_page.html')

        @self.app.route('/operate', methods=['POST'])
        def operate():
            if request.method == 'POST':
                if request.form:
                    logging.info(f'Form: {request.form}')
                    a = request.form['A']
                    b = request.form['B']
                    operator: str = request.form['operator']
                    result: str = self.operate_front_requests(a, b, operator)
                elif request.data:
                    payload = json.loads(json.loads(request.data.decode()))
                    logging.info(f'Payload: {payload}, {request.data}')
                    a = float(payload['A'])
                    b = float(payload['B'])
                    operator: str = payload['operator']
                    result: str = self.operate_front_requests(a, b, operator)
                else:
                    result: str = f'Unsupported HTTP DATA-TYPE: {request}'
            else:
                result: str = f'Unsupported HTTP Method: {request.method}'
            return render_template(
                'main_page.html',
                result=result
            )

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def operate_front_requests(a: int | float, b: int | float, operator: str) -> str:
        """
        front-end user request operator
        :param a: int | float
        :param b: int | float
        :param operator: str
        :return: str
        """
        if a is not None and b is not None and operator is not None:
            base_url: str = 'http://controller:5000/operator'
            payload: dict = {
                'a': a,
                'b': b,
                'operation': operator,
                'status': TaskStatus.queued,
                'uid': str(uuid.uuid4())
            }
            logging.info(f'payload to send: {payload}')
            result: bytes = asyncio.run(post(base_url, payload))
            # make human-readable output
            return f'Result of {operator} A={a} B={b} is {result.decode()}'  # noqa: E501
        else:
            return 'Provide both values A and B'

    def run(self, host: str, port: int, debug: bool):
        """
        method to launch the front-end service
        :param host: str
        :param port: int
        :param debug: bool
        :return:
        """
        self.app.run(host=host, port=port, debug=debug)


def main(host='0.0.0.0', port=5002, debug=True):
    service = FrontEnd(__name__)
    service.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
