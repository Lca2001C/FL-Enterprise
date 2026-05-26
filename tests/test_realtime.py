from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from motopay.realtime.publish import PLATFORM_CHANNEL, publish_event


def test_publish_event_sends_to_redis():
    r = MagicMock()
    with patch("motopay.realtime.publish.get_redis_connection", return_value=r):
        publish_event("alert.new", {"id": "abc", "title": "Test"}, tenant_id=7)
    assert r.publish.call_count == 2
    platform_call = r.publish.call_args_list[0]
    assert platform_call[0][0] == PLATFORM_CHANNEL
    payload = json.loads(platform_call[0][1])
    assert payload["type"] == "alert.new"
    assert r.publish.call_args_list[1][0][0] == "events:operacao:7"
