import asyncio
import json
import uuid
from copy import deepcopy
from random import randint
from urllib import parse

import aiohttp
import pytest
from nats.aio.client import Client
from nats.errors import TimeoutError

from controller.controller import TaskStorage, TaskStatus, Controller, WorkerOperations


async def local_post(url: str, payload: dict, timeout: int = 10) -> bytes:
    """
    Simple POST executor for JSON payload with
    :param timeout: int in seconds 10 seconds by default
    :param url: str
    :param payload: dict
    :return:
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
                url=url,
                headers={'Content-type': 'application/json'},
                json=json.dumps(payload),
                timeout=timeout
        ) as response:
            return await response.content.read()


async def get(url: str, params: dict = None) -> aiohttp.ClientResponse:
    """
    Async get method with retry option
    @param url: target url
    @param params: params for get request
    @return:
    """
    if isinstance(params, dict):
        string_params: str = parse.quote_plus(
            '&'.join('%s=%s' % (k, v) for k, v in params.items()), safe=':/?=&'
        )
        url = f'{url}?{string_params}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()


class TestTaskStorage:
    def setup_class(self):
        self.storage = TaskStorage()
        self.task: dict = {
                'a': randint(50, 100),
                'b': randint(50, 100),
                'operation': 'operator',
                'status': TaskStatus.queued,
                'uid': str(uuid.uuid4())
            }
        self.data = None

    def teardown_class(self):
        del self.storage

    @pytest.mark.unit
    def test_add_new_task(self):
        data = deepcopy(self.task)
        data['uid'] = str(uuid.uuid4())
        result: bool = self.storage.task_add(data)
        assert isinstance(result, bool)
        assert result, "Didn't manage to ADD task, check task_add() logics"  # noqa: E501

    @pytest.mark.unit
    def test_add_negative_delete_field(self):
        data = deepcopy(self.task)
        del data['uid']
        result = self.storage.task_add(data)
        assert isinstance(result, str)
        assert result == 'Error: data structure is incorrect', "Check message ERROR in task_add()"  # noqa: E501

    @pytest.mark.unit
    def test_add_negative_double_add(self):
        data = deepcopy(self.task)
        data['uid'] = str(uuid.uuid4())
        result = self.storage.task_add(data)
        assert isinstance(result, bool)
        assert result is True
        result = self.storage.task_add(data)
        assert isinstance(result, bool)
        assert result is False

    def setup_method(self, method):
        self.data = deepcopy(self.task)
        self.data['uid'] = str(uuid.uuid4())

    def teardown_method(self, method):
        self.data = None

    @pytest.mark.unit
    def test_task_update_status(self):
        saved_status = self.data['status']
        save = self.storage.task_add(self.data)
        assert save is True
        assert saved_status != TaskStatus.running
        result = self.storage.task_update_status(self.data['uid'], TaskStatus.running)
        assert isinstance(result, bool)
        assert result is True
        new_status: str = self.storage.task_get_status(self.data['uid'])
        assert isinstance(new_status, str)
        assert new_status == TaskStatus.running

    @pytest.mark.unit
    def test_task_update_status_not_exist_task(self):
        result = self.storage.task_update_status(self.data['uid'], TaskStatus.running)
        assert isinstance(result, bool)
        assert result is False

    @pytest.mark.unit
    def test_existing_task_get_status(self):
        add = self.storage.task_add(self.data)
        assert add is True
        result: str = self.storage.task_get_status(self.data['uid'])
        assert isinstance(result, str)
        assert result == self.data['status']

    @pytest.mark.unit
    def test_not_exist_task_get_status(self):
        result = self.storage.task_get_status(self.data['uid'])
        assert isinstance(result, bool)
        assert result is False


@pytest.mark.asyncio
class TestController:
    def setup_class(self):
        self.controller = Controller(__name__)
        self.task: dict = {
                'a': randint(50, 100),
                'b': randint(50, 100),
                'operation': 'operator',
                'status': TaskStatus.queued,
                'uid': str(uuid.uuid4())
            }

    def teardown_class(self):
        del self.controller

    @pytest.mark.unit
    async def test_task_handler(self, monkeypatch):
        async def mock(*args, **kwargs):
            return b'48379'

        monkeypatch.setattr(Controller, "task_processor", mock)
        data = deepcopy(self.task)
        data['uid'] = str(uuid.uuid4())

        result: bytes = await self.controller.task_handler(data)
        assert isinstance(result, bytes)
        assert result.decode().isdigit()

    @pytest.mark.unit
    async def test_task_handler_existing_task(self, monkeypatch):
        async def mock(*args, **kwargs):
            return b'48379'

        monkeypatch.setattr(Controller, "task_processor", mock)

        data = deepcopy(self.task)
        data['uid'] = str(uuid.uuid4())
        default_status = None
        data['status'] = default_status

        result: bytes = await self.controller.task_handler(data)
        assert isinstance(result, bytes)
        assert result.decode().isdigit()

        result: bytes = await self.controller.task_handler(data)
        assert isinstance(result, bytes)
        assert result.decode() != default_status
        assert result.decode() == TaskStatus.queued

    data_set = [
        ('wrong_A_type', 2, WorkerOperations.add, None, 'wrong arg type'),
        (1, 'wrong_B_type', WorkerOperations.add, None, 'wrong arg type'),
        (1, 2, 'wrong_operations_value', None, 'Unsupported operation'),
        (1, 2, WorkerOperations.add, TimeoutError, 'Request timed out'),
        (1, 2, WorkerOperations.add, ValueError, 'Unknown problem'),
    ]

    @pytest.mark.unit
    @pytest.mark.parametrize('a, b, operation, mock_obj, expected', data_set)
    async def test_task_processor(self, monkeypatch, a, b, operation, mock_obj, expected):

        async def client_request(*args, **kwargs):
            class NatsMock:
                data = b'48379'
            if mock_obj is None:
                return NatsMock
            else:
                raise mock_obj

        async def client_connection(*args, **kwargs):
            class ClientConnection:
                async def connect(self):
                    return None

            return ClientConnection()

        monkeypatch.setattr(Client, "request", client_request)
        monkeypatch.setattr(Client, "connect", client_connection)

        data = deepcopy(self.task)
        data['uid'] = str(uuid.uuid4())
        data['a'] = a
        data['b'] = b
        data['operation'] = operation

        result: bytes = await self.controller.task_processor(data)
        assert isinstance(result, bytes)
        assert expected in result.decode()


@pytest.mark.asyncio
class TestControllerEndToEnd:

    def setup_class(self):
        self.host = 'http://localhost:5000'
        self.operator_url = f'{self.host}/operator'
        self.get_task_status_url = f'{self.host}/task/status'
        self.options_url = f'{self.host}/controller/options'
        self.task: dict = {
                'a': randint(0, 100),
                'b': randint(1, 100),
                'operation': 'operator',
                'status': TaskStatus.queued,
                'uid': str(uuid.uuid4())
            }

    def teardown_class(self):
        del self.host
        del self.operator_url
        del self.get_task_status_url
        del self.options_url
        del self.task

    get_task_stats_data_set = [
        (WorkerOperations.add, 'DONE'),
        ('FAKE_OPERATION', 'FAILED')
    ]

    @pytest.mark.e2e
    @pytest.mark.parametrize('operation, expected', get_task_stats_data_set)
    async def test_get_task_stats(self, operation, expected):
        data = deepcopy(self.task)
        data['operation'] = operation
        data['uid'] = str(uuid.uuid4())
        result_save = await local_post(url=self.operator_url, payload=data)

        result: dict = await get(url=self.get_task_status_url, params={'uid': data['uid']})
        assert isinstance(result, dict)
        assert result['task_status'] == expected

    @pytest.mark.inregration
    async def test_options(self):
        """
        check operation options
        :return:
        """
        result = await get(url=self.options_url)
        assert isinstance(result, list)
        assert all(isinstance(i, str) for i in result)

    @pytest.mark.e2e
    async def test_operator(self):
        """
        :param a: non-int | non-float
        :param b: non-int | non-float
        :param option: str | int
        :return: bool
        """
        data = deepcopy(self.task)
        data['uid'] = str(uuid.uuid4())
        result = await local_post(url=self.operator_url, payload=data)

        assert isinstance(result, bytes), f"Expected byte string, but got {type(result)}"


if __name__ == '__main__':
    pytest.main()
