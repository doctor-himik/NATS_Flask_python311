import pytest
from allpairspy import AllPairs

from main import task_executor

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
    (1, 0, 'divide', b'Zero division'),
]


@pytest.mark.e2e
@pytest.mark.parametrize('a, b, option, expected', data_set)
def test_happy_path_cli(a, b, option, expected):
    """
    launch docker-compose up and after run E2E tests
    essential happy-path test
    :param a: int | float
    :param b: int | float
    :param option:
    :param expected: int | bytes
    :return: bool
    """
    result: bytes = task_executor(a, b, option)
    assert isinstance(result, bytes), f"Expected to get not decoded string, but got {type(result)}"   # noqa: E501
    if b == 0 and option == 'divide':
        assert result == expected, f'Check ZERO DIVISION logics `{result}`'   # noqa: E501
    else:
        assert float(result.decode()) == expected, f"Check `task_executor` logics is correct"   # noqa: E501


negative_params = [
    ['K', '!', 0],
    ['K', '!'],
    ['add', 'oh_no_test', 123]
]
negative_data_set = [data for data in AllPairs(negative_params)]


@pytest.mark.e2e
@pytest.mark.parametrize('a, b, option', negative_data_set)
def test_negative_cases(a, b, option):
    """
    check negative cases using pairwise
    :param a: non-int | non-float
    :param b: non-int | non-float
    :param option: str | int
    :return: bool
    """
    result: bytes = task_executor(a, b, option)
    assert isinstance(result, bytes), f"Expected byte string, but got {type(result)}"
    err_msg = f'Unsupported operation: `{option}` check -help for proper options'
    assert result.decode() == err_msg or "expected INT or FLOAT" in result.decode()


if __name__ == '__main__':
    pytest.main()