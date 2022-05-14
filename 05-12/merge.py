from collections.abc import Iterable
from multiprocessing import Pool
from typing import Tuple
from datetime import datetime
from functools import wraps


from math import floor
from random import randint
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

    splitted_collection = []
    step = int(len(unordered_collection)/splits)
    for k in range(0, len(unordered_collection), step):
        splitted_collection.append(unordered_collection[k:k + step])
    with Pool(splits) as p:
        ordered_sublists = p.map(_order_col, splitted_collection)

    print(f"Ordered sublists before merges: {ordered_sublists}")
    tupled = make_tuples(ordered_sublists)
    count = 0
    while(len(tupled) > 1):
        with Pool(splits) as p:
            merged_sublists = p.map(merge, tupled)
        print(f"Merged sublists on iteraction: {count}\n{merged_sublists}")
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
    # Merga até algum ficar vazio
    while a and b:
        if a[0] < b[0]:
            ret.append(a.pop(0))
        else:
            ret.append(b.pop(0))

    # Passa o resto do que não ficou vazio
    if a:
        for i in a: ret.append(i)
    else:
        for i in b: ret.append(i)

    return ret

if __name__ == "__main__":
    assert len(sys.argv) == 3, "Nº errado de argumentos parça! Tem que ser só 2"

    k, n = map(int, sys.argv[1:])

    random_vet = [randint(1 << 0, 1 << 10) for _ in range(n)]
    print(parallel_universe(random_vet, k))
