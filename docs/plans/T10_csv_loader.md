# T10: CSV OHLCV Loader + Normalization + Validation Report

**Agent:** A2 (Data + Backtest Core)
**Status:** Draft
**Priority:** Foundation (blocks T20, T40)

---

## Objective

Add CSV file loading support alongside the existing Binance API loader, normalize incoming CSV data to the internal OHLCV schema defined in `shared/contracts.py`, and produce a structured validation report covering data quality checks.

---

## Current State

- `data/loader.py` fetches OHLCV data exclusively from the Binance REST API.
- Fetched data is cached as Parquet files in `.cache/ohlcv/` with key format `{symbol}_{timeframe}_{start}_{end}.parquet`.
- `data/validation.py` performs basic data quality checks (gaps, duplicates, monotonicity).
- The `OHLCV` dataclass in `shared/contracts.py` defines the canonical schema: `timestamp`, `open`, `high`, `low`, `close`, `volume`.

---

## Plan

### 1. CSV Loading (`data/loader.py`)

Add a `load_csv(path: str, symbol: str, timeframe: str) -> pd.DataFrame` method that:

- Reads a CSV file using `pd.read_csv` with explicit dtype mapping.
- Supports common column naming conventions via a column alias map:
  - `timestamp` / `date` / `datetime` / `time` / `open_time` -> `timestamp`
  - `open` / `Open` / `o` -> `open`
  - `high` / `High` / `h` -> `high`
  - `low` / `Low` / `l` -> `low`
  - `close` / `Close` / `c` -> `close`
  - `volume` / `Volume` / `vol` / `v` -> `volume`
  - `quote_volume` / `quote_vol` (optional) -> `quote_volume`
- Raises `ValueError` with a descriptive message if required columns cannot be mapped.
- Attaches `symbol` and `timeframe` as metadata (stored as DataFrame attrs or additional columns depending on downstream needs).

### 2. Timestamp Normalization

- Parse timestamps from multiple formats: Unix epoch (seconds and milliseconds), ISO 8601 strings, and common date formats (`YYYY-MM-DD HH:MM:SS`).
- Convert all timestamps to UTC `datetime64[ms]` (millisecond precision, timezone-aware).
- Sort DataFrame by timestamp ascending after parsing.
- Strip timezone info after conversion to UTC to match existing Binance loader output format.

### 3. Schema Normalization

Ensure the output DataFrame matches the exact schema expected by the backtest engine:

| Column         | Type      | Required | Notes                              |
|----------------|-----------|----------|------------------------------------|
| `timestamp`    | datetime64[ms] | Yes | UTC, monotonically increasing     |
| `open`         | float64   | Yes      |                                    |
| `high`         | float64   | Yes      |                                    |
| `low`          | float64   | Yes      |                                    |
| `close`        | float64   | Yes      |                                    |
| `volume`       | float64   | Yes      | >= 0                               |
| `quote_volume` | float64   | No       | Defaults to 0.0 if absent          |

- Cast numeric columns with `pd.to_numeric(errors='coerce')` and track coercion failures.
- Drop rows where all OHLCV values are NaN (header artifacts, blank lines).
- Preserve rows with partial NaN for inclusion in the validation report.

### 4. Validation Checks (`data/validation.py`)

Enhance the existing validation module to produce a `ValidationReport`:

```python
@dataclass
class ValidationIssue:
    severity: str          # "error" | "warning"
    row_index: int | None  # None for global issues
    column: str | None
    message: str

@dataclass
class ValidationReport:
    valid: bool                    # True if no errors (warnings allowed)
    row_count: int
    date_range_start: str          # ISO 8601
    date_range_end: str            # ISO 8601
    issues: list[ValidationIssue]
```

Checks to implement:

| Check                          | Severity | Description                                                     |
|-------------------------------|----------|-----------------------------------------------------------------|
| Monotonic timestamps          | error    | Each timestamp must be strictly greater than the previous       |
| No duplicate timestamps       | error    | No two rows share the same timestamp                            |
| No gaps beyond expected interval | warning | Flag gaps > 2x the expected candle interval                   |
| OHLC constraint               | error    | `low <= min(open, close)` and `high >= max(open, close)`       |
| Volume non-negative           | error    | `volume >= 0` for every row                                    |
| NaN values in required columns| error    | Any NaN in open/high/low/close/volume after coercion           |
| Minimum row count             | warning  | Warn if fewer than 100 bars (backtest may be unreliable)       |
| Timestamp timezone presence   | warning  | Warn if timestamps appear timezone-naive                       |

### 5. Integration with Existing Loader

- Add a unified `load_data()` function or extend the existing one with a `source` parameter:
  - `source="binance"` (default): existing Binance API path
  - `source="csv"`: new CSV loading path
- Both paths feed into the same validation pipeline and produce the same output format.
- CSV-loaded data can optionally be cached to Parquet using the same caching mechanism.

---

## Files to Modify

| File                  | Change                                                        |
|-----------------------|---------------------------------------------------------------|
| `data/loader.py`      | Add `load_csv()`, column alias mapping, timestamp parsing    |
| `data/validation.py`  | Add `ValidationReport`, `ValidationIssue`, enhanced checks   |
| `shared/contracts.py` | **NO CHANGES** (frozen contract)                             |

## Files to Create

| File                           | Purpose                                      |
|--------------------------------|----------------------------------------------|
| `tests/test_data_loader.py`    | Unit tests for CSV loading and normalization |
| `tests/fixtures/sample_ohlcv.csv` | Standard-format test fixture              |
| `tests/fixtures/sample_ohlcv_alt_columns.csv` | Alternate column names fixture  |
| `tests/fixtures/sample_ohlcv_bad_data.csv` | Fixture with intentional errors       |

---

## Test Plan

1. **Happy path**: Load a well-formed CSV, verify output DataFrame matches OHLCV schema exactly.
2. **Column alias resolution**: Load CSV with alternate column names (`Open`, `High`, `Vol`, etc.), verify correct mapping.
3. **Timestamp formats**: Test Unix epoch (seconds), Unix epoch (milliseconds), ISO 8601, and `YYYY-MM-DD HH:MM:SS`.
4. **Validation report - clean data**: Confirm `valid=True` and empty issues list for good data.
5. **Validation report - bad data**: Inject duplicate timestamps, OHLC violations, negative volume, NaN values. Confirm each issue is reported with correct severity and row index.
6. **Gap detection**: Create data with a 3-candle gap in 1h timeframe, verify warning is raised.
7. **Empty/minimal CSV**: Test with 0 rows, 1 row, and the minimum-warning threshold.
8. **Missing required columns**: Verify `ValueError` with descriptive message.
9. **Integration**: Verify CSV-loaded data can be passed directly to the backtest engine without transformation.

---

## Risks and Mitigations

| Risk                                         | Likelihood | Impact | Mitigation                                           |
|----------------------------------------------|-----------|--------|------------------------------------------------------|
| Different CSV formats from different exchanges | High     | Medium | Column alias map covers major exchanges; raise clear errors for unmappable columns |
| Timestamp timezone handling inconsistencies    | Medium   | High   | Always convert to UTC; warn on timezone-naive inputs; document expected format |
| Large CSV files causing memory issues          | Low      | Medium | Use chunked reading for files > 100MB; document size limits |
| Parquet cache key collisions with CSV data     | Low      | Low    | Include source type in cache key if CSV caching is enabled |

---

## Dependencies

- **Upstream:** `shared/contracts.py` (OHLCV schema) - frozen, no changes needed
- **Downstream:** T20 (backtest engine consumes the DataFrame output from this loader)

---

## Acceptance Criteria

- [ ] `load_csv()` successfully loads CSVs with at least 3 different column naming conventions
- [ ] All timestamps normalized to UTC datetime64[ms]
- [ ] `ValidationReport` correctly identifies all 8 check categories
- [ ] CSV-loaded data is byte-compatible with Binance-loaded data for the backtest engine
- [ ] All tests pass with `pytest tests/test_data_loader.py -v`
