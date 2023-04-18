import json
import uuid

import pytest

from controller.controller import TaskStatus
from worker.worker import Worker


@pytest.mark.asyncio
class TestWorker:
    def setup_class(self):
        self.worker = Worker()

    def teardown_class(self):
        del self.worker

    calc_data_set = [
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
        (-1, -0.01, 'divide', 100.0),
        (0, 2, 'divide', 0.0),  # funny case
        (1, 0, 'divide', 'Zero division'),
    ]

    @pytest.mark.unit
    @pytest.mark.parametrize('a, b, operator, expected', calc_data_set)
    async def test_calculator(self, a, b, operator, expected):
        run_delay = False
        result = await self.worker.calculator(a, b, operator, run_delay)
        assert isinstance(result, type(expected))
        assert result == expected

    calc_data_set = [
        (1, 'test', 'add', 'Incorrect payload'),
        ('test', -2, 'add', 'Incorrect payload'),
        ('test', -2, '150050', 'Incorrect payload'),
    ]

    @pytest.mark.unit
    @pytest.mark.parametrize('a, b, operator, expected', calc_data_set)
    async def test_processor(self, a, b, operator, expected, monkeypatch):

        class NatsPublisherMock:
            async def publish(*args, **kwargs):
                assert expected in args[-1].decode(), 'ERROR message expected'
                return args, kwargs

        self.worker.nats_connection = NatsPublisherMock()

        class MsgTest:
            def __init__(self):
                self.data = None
                self.reply = b'test_mock'

        msg = MsgTest()
        msg.data = json.dumps({
            'a': a,
            'b': b,
            'operation': operator,
            'status': TaskStatus.queued,
            'uid': str(uuid.uuid4())
        }).encode()

        await self.worker.processor(msg=msg)


if __name__ == '__main__':
    pytest.main()
