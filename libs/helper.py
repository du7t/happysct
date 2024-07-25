"""Common methods"""

import json
from time import time

import psutil
from requests.exceptions import ConnectionError, HTTPError

import libs.memory as mem
import conf.settings as settings


def get_feature_flag(name='', module=None):
    return module.__dict__.get(name, None)


def get_ff(name=''):
    assert name
    return get_feature_flag(name=name, module=settings)


def arg_to_list(arg: tuple | str) -> list:
    return list(arg) if isinstance(arg, tuple) else arg.split(",")


def retry_on_exceptions(exception: Exception) -> bool:
    retry_status_codes = [408, 429, 500, 502, 503, 504]
    return (
        isinstance(exception, ConnectionError)
        or isinstance(exception, HTTPError)
        and exception.response.status_code in retry_status_codes
    )


def load_json(file_path) -> dict:
    with open(file_path, "r") as f:
        return json.load(f)


def get_health():

    def pretty(value, divider=1024 * 1024, digits=0):
        return round(value / divider, digits)

    process = psutil.Process()
    workers = process.parent().children(recursive=True)
    parent_uptime = round(time() - process.parent().create_time(), 1)
    workers_count = len(workers)
    workers_data = dict()
    uptime_diff = 0
    for worker in workers:
        worker_uptime = round(time() - worker.create_time(), 1)
        workers_data[worker.pid] = {
            'name': worker.name(),
            'uptime': worker_uptime,
            'rss': pretty(worker.memory_info().rss)
        }

        if parent_uptime - worker_uptime > 0.5:
            uptime_diff = parent_uptime - worker_uptime

    memory_max_usage = pretty(mem.get_max_memory_usage())
    memory_usage = pretty(mem.get_memory_usage())
    memory_limit = pretty(mem.get_memory_limit())

    message = ['I am fine']
    if memory_limit > 0 and (memory_usage / memory_limit) > 0.8:
        message.append('Memory usage looks high')
    if uptime_diff > 0:
        message.append('Workers are lagging, compare uptimes')

    data = {
        "message": message,
        "info": "data sizes are in megabytes, timings are in seconds",
        'memory_max_usage': memory_max_usage,
        'memory_usage': memory_usage,
        'memory_limit': memory_limit,
        'workers_count': workers_count,
        'workers_data': workers_data,
        'parent': process.parent().name(),
        'parent_uptime': parent_uptime,
        'parent_rss': pretty(process.parent().memory_info().rss),
    }
    return data
