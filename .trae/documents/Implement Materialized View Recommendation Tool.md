## Implementation Plan: recommend\_materialized\_views Tool

### 1. Core Functionality

* Analyze `pg_stat_statements` for complex, frequently-run queries

* Identify tables with favorable read/write ratios for materialization

* Generate CREATE MATERIALIZED VIEW commands with proper indexes

* Suggest refresh schedules based on data volatility patterns

### 2. Implementation Details

* Add `recommend_materialized_views(schema=None, min_query_time=1000, min_frequency=10)` function

* Query complexity detection via SQL parsing heuristics

* Access pattern analysis using pg\_stat\_user\_tables scan ratios

* Refresh strategy recommendations (HOURLY/DAILY/NEVER)

* Fallback behavior when pg\_stat\_statements unavailable

### 3. Code Structure

```python
@mcp.tool
def recommend_materialized_views(
    schema: str | None = None,
    min_query_time: int = 1000,  # milliseconds
    min_frequency: int = 10,      # minimum query executions
    min_size_mb: int = 100         # minimum table size to consider
) -> list[dict[str, Any]]:
    """
    Analyzes database access patterns and recommends tables for materialized view conversion.
    
    Returns recommendations with:
    - table_name and schema
    - suggested_materialized_view_name
    - create_sql with appropriate indexes
    - refresh_strategy (HOURLY/DAILY/WEEKLY/NEVER)
    - performance_benefit_estimate
    - storage_impact_estimate
    """
```

### 4. Documentation Updates

* Add tool to README.md tools list

* Include usage examples for capacity planning

* Add to example prompts section

### 5. Validation

* Syntax check with python -m compileall

* Test with existing diagnostic tools

* Verify integration with current

