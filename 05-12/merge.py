from math import floor
from typing import Tuple
from random import randint
from datetime import datetime
from functools import wraps
from multiprocessing import Pool
from collections.abc import Iterable

import sys

def timer(func):
    @wraps(func)
    def _time_it(*args, **kwargs):
        start = datetime.now()
        try:
            return func(*args, **kwargs)
        finally:
            tempo = datetime.now() - start
            print(f"TEMPO | {func.__name__} | {tempo.total_seconds()}")

    return _time_it


def _order_col(col: Iterable):
    col.sort()
    print(f"Número de elementos ordenados: {len(col)}")
    return col


def _random_vector(size: int):
    return [randint(1 << 0, 1 << 32) for _ in range(size)]

@timer
def parallel_universe(unordered_collection: Iterable, splits: int):

    def make_tuples(ordered_sublists: Iterable):
        tupled = []
        splits = len(ordered_sublists)
        for i in range(floor(splits/2)):
            tupled.append((ordered_sublists[2*i], ordered_sublists[2*i+1]))

        if splits%2 == 1:
            tupled.append((ordered_sublists[-1], ))

        return tupled

    step = int(len(unordered_collection)/splits)
    # Correção pra qndo `step == 0` (mais processos q elementos na lista)
    if step == 0: step = 1

    splitted_collection = []
    for k in range(0, len(unordered_collection), step):
        splitted_collection.append(unordered_collection[k:k + step])
    with Pool(splits) as p:
        ordered_sublists = p.map(_order_col, splitted_collection)

    with open("output.txt", "w") as f:
        print(f"Ordered sublists before merges:", file=f)
        for l in ordered_sublists:
            print(l, file=f)

    tupled = make_tuples(ordered_sublists)
    count = 0
    while(len(tupled) > 1):
        with Pool(splits) as p:
            merged_sublists = p.map(merge, tupled)

        with open("output.txt", "a") as f:
            print(f"Merged sublists on iteraction {count}:", file=f)
            for l in merged_sublists:
                print(l, file=f)

        tupled = make_tuples(merged_sublists)
        count = count + 1
    ordered_collection = merge(tupled[0])

    return ordered_collection


@timer
def merge(lists: Tuple[Iterable, Iterable]) -> Iterable:
    if len(lists) == 1: return lists[0]

    assert len(lists) == 2, "?????????????????????"

    ret = []
    a, b = lists
    a_size, a_i = len(a), 0
    b_size, b_i = len(b), 0
    # Merga até algum ficar vazio
    while a_i < a_size and b_i < b_size:
        if a[a_i] < b[b_i]:
            ret.append(a[a_i])
            a_i += 1
        else:
            ret.append(b[b_i])
            b_i += 1

    # Passa o resto do que não ficou vazio
    if a_i < a_size: ret += a[a_i:]
    else:            ret += b[b_i:]

    return ret

if __name__ == "__main__":
    assert len(sys.argv) == 3, "Nº errado de argumentos parça! Tem que ser só 2"

    k, n = map(int, sys.argv[1:])

    random_vet = _random_vector(n)
    ord_list = parallel_universe(random_vet, k)

    # Checa se a lista está ordenada
    assert all(ord_list[i] <= ord_list[i+1] for i in range(n - 1)),\
        "Algo de errado não está certo, a lista final não está ordenada"

    with open("output.txt", "a") as f:
        print(f"Ordered list:\n{ord_list}", file=f)
