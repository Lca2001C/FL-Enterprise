#!/usr/bin/env python3
"""Stress script: enqueue many no-op style tasks (requires running worker)."""
from __future__ import annotations

import argparse

from motopay.infrastructure.messaging.celery_app import celery_app


@celery_app.task(name="motopay.scripts.stress.noop")
def noop_task(i: int) -> int:
    return i


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    args = parser.parse_args()
    for i in range(args.count):
        noop_task.apply_async(args=[i], queue="default")
    print(f"Enqueued {args.count} noop tasks")


if __name__ == "__main__":
    main()
