# Test Failure Digest

**Runner detected:** `pytest`
**Source log:** `reports/qa/goal-auto-money-printer-iter-4-fullsuite.log`

## Failing Tests (1 shown)

### 1. `test_write_and_read_full_round_trip`
- **Location:** `tests/test_directions_cache.py:98`

**Error:**
```
assert 0 == 1
+  where 0 = len([])
```

<details><summary>Traceback excerpt</summary>

```
def test_write_and_read_full_round_trip():
        cache_key = "test_round_trip"
        node = _make_node("strategy-5", total_return=0.42)
    
        dc.write_direction_result(cache_key, 5, "strategy-5", node)
    
        result = dc.read_direction_full(cache_key, "strategy-5")
        assert result is not None
        assert result["id"] == "strategy-5"
        assert result["prompt"] == "Test prompt for strategy-5"
        assert result["scriptCode"] == "# Strategy: strategy-5"
        assert result["strategyName"] == "Strategy strategy-5"
        assert result["status"] == "complete"
        assert result["result"]["total_return"] == pytest.approx(0.42)
>       assert len(result["timeframeResults"]) == 1
E       assert 0 == 1
E        +  where 0 = len([])

tests/test_directions_cache.py:98: AssertionError
```

</details>

## Recently modified files (likely in scope)

- `apps/backend/backend/auto_session.py`
- `apps/backend/shared/model_catalog.py`
- `apps/backend/tests/test_auto_session.py`
- `apps/backend/tests/test_model_pricing.py`
- `runs/goal-session-auto-money-printer/telemetry.jsonl`
- `runs/goal-session-auto-money-printer/trace/.next-step`
- `runs/goal-session-auto-money-printer/trace/trace.jsonl`
- `apps/backend/backend/cost_tracker.py`
- `apps/backend/backend/pipeline.py`
- `apps/backend/shared/llm_usage.py`

## Suggested next reads (for the dev agent)

1. `tests/test_directions_cache.py:98` — failing test
2. `apps/backend/backend/auto_session.py` — recently modified
3. `apps/backend/shared/model_catalog.py` — recently modified
4. `apps/backend/tests/test_auto_session.py` — recently modified
