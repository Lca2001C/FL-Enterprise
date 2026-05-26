from __future__ import annotations

from unittest.mock import MagicMock, patch

from motopay.infrastructure.messaging import celery_observability as obs


class MagicMockTask:
    name = "task.test"


def test_task_postrun_counts_failure_state():
    with patch.object(obs.celery_tasks_total, "labels") as labels_mock:
        counter = labels_mock.return_value
        obs._task_times["tid-1"] = 0
        obs.task_postrun_handler(task_id="tid-1", task=MagicMockTask(), state="FAILURE")
        labels_mock.assert_called_with(task_name="task.test", status="failure")
        counter.inc.assert_called_once()


def test_task_postrun_counts_success_state():
    with patch.object(obs.celery_tasks_total, "labels") as labels_mock:
        counter = labels_mock.return_value
        obs._task_times["tid-2"] = 0
        obs.task_postrun_handler(task_id="tid-2", task=MagicMockTask(), state="SUCCESS")
        labels_mock.assert_called_with(task_name="task.test", status="success")
        counter.inc.assert_called_once()


def test_get_dlq_reads_redis():
    r = MagicMock()
    r.lrange.return_value = ["t1"]
    r.hgetall.return_value = {
        "task_id": "t1",
        "task_name": "task.x",
        "args": "[]",
        "kwargs": "{}",
        "error": "boom",
        "retry_count": "3",
        "timestamp": "1.0",
        "status": "pending_review",
    }
    with patch(
        "motopay.infrastructure.messaging.celery_observability.get_redis_connection",
        return_value=r,
    ):
        items = obs.get_dlq()
    assert len(items) == 1
    assert items[0]["task_name"] == "task.x"
