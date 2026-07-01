"""最近点检索基准；不读写工程文件。"""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aprepost2.services.search import _nearest_indices


def main() -> None:
    generator = np.random.default_rng(20260701)
    nodes = generator.random((50_000, 3))
    queries = generator.random((200, 3))

    _nearest_indices(nodes[:100], queries[:1])  # 排除首次导入 SciPy 的时间
    started = perf_counter()
    indexed = _nearest_indices(nodes, queries)
    indexed_seconds = perf_counter() - started

    started = perf_counter()
    brute = np.asarray(
        [np.argmin(np.sum((nodes - query) ** 2, axis=1)) for query in queries]
    )
    brute_seconds = perf_counter() - started

    if not np.array_equal(indexed, brute):
        raise RuntimeError("空间索引与全遍历的最近点结果不一致")
    print(f"节点数: {len(nodes):,}，查询点数: {len(queries):,}")
    print(f"cKDTree: {indexed_seconds:.6f} s")
    print(f"全遍历: {brute_seconds:.6f} s")
    print(f"加速比: {brute_seconds / indexed_seconds:.2f}x")


if __name__ == "__main__":
    main()
