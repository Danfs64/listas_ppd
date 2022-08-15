from ..settings import *
from ..domain import Queue
from typing import Callable, Any, Collection


def set_exchange(chann, exchange: str, exchange_type: str) -> str:
    chann.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    queue = chann.queue_declare(queue="", exclusive=True)

    queue_name = queue.method.queue
    chann.queue_bind(exchange=exchange, queue=queue_name)
    return queue_name


def publish(exchange: Queue, body: str) -> None:
    MANAGING_CHANN.publish(exchange=exchange, routing_key="", body=body)


# gambiarra pq o sistema de tipos de python é um lixo
blocking = type(MANAGING_CHANN)


def get(
    get_func: Callable[[Any], (bool, Collection | int)],
    queue,
    args: list,
    collection=None,
):
    body_gen = MANAGING_CHANN.consume(queue)

    loop_again = True
    while loop_again:
        _, _, body = next(body_gen)
        loop_again, collection = get_func(body, collection, *args)
    MANAGING_CHANN.cancel()
    return collection
