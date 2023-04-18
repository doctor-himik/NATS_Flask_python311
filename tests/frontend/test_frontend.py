import asyncio
import json
import time
from random import randint

import aiohttp
import pytest
from allpairspy import AllPairs

from controller.controller import WorkerOperations
from frontend import frontend
from frontend.frontend import FrontEnd


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

data_set = [
    (1, 2, 'add', 3),
    (1, -2, 'add', -1),
    (-1, -2, 'add', -3),
    (0.01, 0.1, 'add', 0.11),
    (0, -1, 'subtract', 1),
    (-1, -2, 'subtract', 1),
    (0, 0, 'subtract', 0),
    (19, 10, 'subtract', 9),
    (0, 0, 'multiply', 0),
    (0, 2, 'multiply', 0),
    (1, 2, 'multiply', 2),
    (5, 0.5, 'multiply', 2.5),
    (-1, -2, 'multiply', 2),
    (-1, 2, 'divide', -0.5),
    (-1, -0.01, 'divide', 100),
    (0, 2, 'divide', 0),
    (1, 0, 'divide', 'Zero division'),
]


@pytest.mark.e2e
@pytest.mark.parametrize('a, b, option, expected', data_set)
def test_happy_path_frontend(a, b, option, expected):
    """
    check negative cases using pairwise
    :param a: non-int | non-float
    :param b: non-int | non-float
    :param option: str | int
    :return: bool
    """
    url = 'http://localhost:5002/operate'
    payload = {
        'A': a,
        'B': b,
        'operator': option
    }
    result = asyncio.run(local_post(url=url, payload=payload))

    assert isinstance(result, bytes), f"Expected byte string, but got {type(result)}"
    assert f' is {expected}' in result.decode() or "expected INT or FLOAT" in result.decode()


params = [
    [3, 0, -1],
    [-1, 0, 17],
    ['add', 'divide', 'multiply']
]
data_set = [data for data in AllPairs(params)]


@pytest.mark.skip('not finished and not that vital')
@pytest.mark.e2e
@pytest.mark.parametrize('a, b, option', data_set)
def test_negative_cases(a, b, option):
    """
    check negative cases using pairwise
    :param a: non-int | non-float
    :param b: non-int | non-float
    :param option: str | int
    :return: bool
    """
    url = 'http://localhost:5002/operate'
    payload = {
        'A': a,
        'B': b,
        'operator': option
    }
    result = asyncio.run(local_post(url=url, payload=payload))

    assert isinstance(result, bytes), f"Expected byte string, but got {type(result)}"
    err_msg = f'Unsupported operation: `{option}` check -help for proper options'
    assert result.decode() == err_msg or "expected INT or FLOAT" in result.decode()


class TestFrontEnd:
    def setup_class(self):
        self.server = FrontEnd(__name__)

    def teardown_class(self):
        del self.server

    data_set = [
        (1, 5, WorkerOperations.add, '6'),
        (1, 5, WorkerOperations.multiply, '5'),
        (1, 5, WorkerOperations.subtract, '-4'),
        (1, 5, WorkerOperations.divide, '0.2'),
        (1, 0, WorkerOperations.divide, 'Zero division'),
        (None, 5, WorkerOperations.add, 'Provide both values A and B'),
        (1, None, WorkerOperations.add, 'Provide both values A and B'),
        (1, 5, None, 'Provide both values A and B'),
    ]

    @pytest.mark.unit
    @pytest.mark.parametrize('a, b, operator, expected', data_set)
    def test_frontend_launches_fine(self, a, b, operator, expected, monkeypatch):
        async def mock(*args, **kwargs):
            return str(expected).encode()

        monkeypatch.setattr(frontend, "post", mock)

        result: str = self.server.operate_front_requests(a, b, operator)
        assert isinstance(result, str)
        assert expected in result

    @pytest.mark.unit
    def test_cache_on_front(self, monkeypatch):
        sleep = 2

        async def mock(*args, **kwargs):
            await asyncio.sleep(sleep)
            return b'777'

        monkeypatch.setattr(frontend, "post", mock)

        a, b, operator = -randint(1, 10**6), randint(1**3, 10**6), WorkerOperations.add

        start_non_cache = time.time_ns()
        non_cache = self.server.operate_front_requests(a, b, operator)
        finish_non_cache = time.time_ns()

        start_cache = time.time_ns()
        cache = self.server.operate_front_requests(a, b, operator)
        finish_cache = time.time_ns()

        assert non_cache == cache
        print(f"NON-CACHED: {(finish_non_cache-start_non_cache)/1000000000}")
        print(f"CACHED: {finish_cache - start_cache}")
        assert (finish_non_cache-start_non_cache)/1000000000 > sleep
        assert finish_non_cache - start_non_cache > finish_cache - start_cache


if __name__ == '__main__':
    pytest.main()
