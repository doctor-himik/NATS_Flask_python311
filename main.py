#!/usr/bin/env python3.11
# -*- coding: UTF-8 -*-
import argparse
import asyncio
import json
import logging
import os
import sys
import uuid

import aiohttp

choices = ['add', 'subtract', 'multiply', 'divide']
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


async def get(url: str):
    """
    Make a GET request to service
    :param url:
    :return:
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.content.read()


async def post(url: str, payload: dict, timeout: int = 10) -> bytes:
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


def task_executor(a: int, b: int, operator: str) -> bytes:
    """
    Runs requests to controller
    :param a: int or float
    :param b: int or float
    :param operator: str
    :return: bytes
    """
    base_url: str = 'http://localhost:5000/operator'
    payload: dict = {
        'a': a,
        'b': b,
        'operation': operator,
        'status': TaskStatus.queued,
        'uid': str(uuid.uuid4())
    }

    return asyncio.run(post(base_url, payload))


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


def cli_launcher() -> str:
    """
    CLI for 'add', 'subtract', 'multiply', 'divide' operations between two params A and B
    :return: str
    """
    parser = argparse.ArgumentParser(description="Simple CLI for test purposes.")  # noqa: E501
    parser.add_argument(
        '-operator',
        required=True,
        help=f"Available operations: `{'` `'.join(choices)}` Example '-operator add 334 -19'",  # noqa: E501
        nargs='+',
    )
    args = parser.parse_args()

    if args.operator[0] not in choices:
        logging.warning(f"Operation: '{args.operator[0]}' is not supported, please check -help ")  # noqa: E501
        sys.exit(1)

    elif len(args.operator) != 3:
        logging.warning(
            f"Unexpected amount of arguments: '{args.operator}' specify properly 2 like: '-operator multiply 17 844")  # noqa: E501
        sys.exit(1)
    elif not arg_check(args.operator[1]) or not arg_check(args.operator[2]):
        logging.warning(
            f"Unexpected arg type: '{args.operator[1]}', '{args.operator[2]}' only numeric accepted")  # noqa: E501
        sys.exit(1)
    elif args.operator[-1] == 0 and args.operator[1] == choices[-1]:  # choices[-1] == divide MAKE SURE
        logging.warning(f"Zero division detected, other valid options")  # noqa: E501
        sys.exit(1)

    result: bytes = task_executor(
        a=args.operator[1],
        b=args.operator[2],
        operator=args.operator[0]
    )
    # make human-readable output
    user_message: str = f'Result of {args.operator[0]} a={args.operator[1]} b={args.operator[2]} is {result.decode()}'  # noqa: E501
    logging.info(user_message)
    return user_message


if __name__ == '__main__':
    cli_launcher()
