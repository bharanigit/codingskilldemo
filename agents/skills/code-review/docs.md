# Databricks Code Review — Full Checklist

# 1. Review Scope

Determine which technologies are present:

- Python
- PySpark
- Spark SQL
- Databricks notebooks
- Delta Lake
- Structured Streaming
- Auto Loader
- Lakeflow
- Unity Catalog
- Databricks Jobs
- Serverless compute
- Photon
- SQL Warehouse

Apply only the relevant checks.

---

# 2. Review Priorities

Review in this order:

1. Correctness
2. Security
3. Reliability
4. Performance
5. Cost
6. Maintainability
7. Readability
8. Databricks best practices

Prioritize issues that can materially affect production workloads.

---

# 3. Severity

Use only these severity levels:

## Critical

Use only for issues that can cause:

- Data loss
- Severe data corruption
- Credential exposure
- Major security vulnerability
- Production-wide failure

## High

Use for:

- Driver Out Of Memory risk
- Large-scale `collect()`
- Large-scale `toPandas()`
- Cartesian joins
- Unbounded streaming state
- Incorrect Delta MERGE logic
- Hardcoded credentials
- Major correctness issues
- Severe performance problems

## Medium

Use for:

- Unnecessary shuffle
- Inefficient joins
- Excessive caching
- Python UDF where native Spark functions exist
- Poor partitioning
- Unnecessary Spark actions
- Significant maintainability problems

## Low

Use for:

- Naming
- Formatting
- Minor duplication
- Minor readability issues
- Unused imports
- Missing useful comments

Do not inflate severity.

---

# 4. General Python Code Quality

Check for:

- Poor naming
- Long functions
- Large classes
- Duplicate code
- Dead code
- Unused imports
- Unused variables
- Magic numbers
- Hardcoded configuration
- Excessive nesting
- Poor modularization
- Mutable global state
- Inconsistent error handling

Prefer:

- Small focused functions
- Meaningful names
- Reusable modules
- Configuration-driven behavior
- Clear separation of concerns

---

# 5. Readability

Identify:

- Ambiguous variable names
- Overly complex expressions
- Excessive nesting
- Very long functions
- Poorly structured notebooks
- Repeated inline logic

Prefer code that is easy for another engineer to understand and maintain.

Do not recommend abstraction merely for the sake of abstraction.

---

# 6. Naming

Check:

- Variables
- Functions
- Classes
- DataFrame names
- Columns
- Configuration variables

Prefer names such as:

```python
customer_df
transaction_df
customer_id
transaction_date
load_customer_data()
```

Avoid:

```python
df1
df2
x
tmp
data1
```

unless the scope is extremely small and obvious.

---

# 7. Modularization

Identify functions that perform too many responsibilities.

For example:

```python
def process_data():
    # read
    # validate
    # transform
    # join
    # write
    # notify
```

Recommend separating responsibilities where appropriate:

```python
def read_data():
    ...

def validate_data():
    ...

def transform_data():
    ...

def write_data():
    ...
```

Do not over-engineer simple code.

---

# 8. Duplicate Code

Look for:

* Repeated transformations
* Repeated SQL
* Repeated validation
* Repeated configuration
* Copy/paste functions

Recommend reusable functions only when duplication is meaningful.

---

# 9. Exception Handling

Check for:

```python
try:
    ...
except:
    ...
```

Flag:

* Bare `except`
* Swallowed exceptions
* Missing logging
* Incorrect exception handling
* Continuing after a critical failure

Prefer:

```python
try:
    process_data()
except ValueError as exc:
    logger.exception("Invalid input data")
    raise
```

Never silently ignore failures.

---

# 10. Logging

Check for:

* Excessive `print()`
* Missing logging
* Logging sensitive information
* Missing error context

Prefer:

```python
logger.info("Starting customer ingestion")
logger.info("Processing source: %s", source_name)
```

Never log:

* Passwords
* Tokens
* API keys
* Secrets
* Sensitive personal information

---

# 11. PySpark Driver-Side Operations

Identify:

```python
collect()
toPandas()
take()
head()
first()
rdd.collect()
```

Pay particular attention to:

```python
rows = df.collect()

for row in rows:
    ...
```

These operations can move distributed data to the Spark driver.

Severity:

* High if data can be large or unbounded
* Medium if size is uncertain
* Low if explicitly bounded

Acceptable example:

```python
rows = (
    df
    .select("customer_id")
    .limit(100)
    .collect()
)
```

Do not flag bounded driver-side operations automatically.

---

# 12. display()

Check for:

```python
display(df)
```

Do not automatically classify `display()` as an error.

Determine whether the code is:

* Interactive development
* Debugging
* Production notebook
* Scheduled job
* Reusable library

Flag `display()` when it is inappropriate for production execution.

Recommendation:

```python
logger.info("Customer processing completed")
```

instead of relying on interactive display.

---

# 13. print()

Check for:

```python
print(...)
```

In production code, prefer structured logging.

Do not flag simple temporary debugging code unless the code is clearly production-bound.

---

# 14. Spark Actions

Identify unnecessary actions such as:

```python
count()
collect()
show()
take()
first()
```

Remember that Spark actions can trigger execution.

Example:

```python
logger.info("Rows: %s", df.count())
```

may introduce an additional Spark job.

Do not flag `count()` when it is required as a business metric or validation step.

---

# 15. repartition()

Review:

```python
df.repartition(...)
```

Check:

* Whether repartition is necessary
* Partition count
* Shuffle cost
* Downstream operations
* Data volume

Potential concern:

```python
df.repartition(1000)
```

Do not recommend a specific partition count without understanding workload characteristics.

---

# 16. coalesce()

Review:

```python
df.coalesce(...)
```

Pay special attention to:

```python
df.coalesce(1)
```

This can severely reduce parallelism.

Flag as High when it creates a significant production performance bottleneck.

---

# 17. Caching

Review:

```python
cache()
persist()
unpersist()
```

Flag:

* Caching data used once
* Excessive caching
* Caching extremely large datasets
* Missing `unpersist()`
* Multiple unnecessary cached DataFrames

Example:

```python
df.cache()

result = df.filter(...)
```

If `df` is only used once, caching may be unnecessary.

Do not recommend caching without evidence of reuse.

---

# 18. Join Review

Inspect every join.

Check for:

* Missing join conditions
* Cartesian joins
* Large-to-large joins
* Data skew
* Unnecessary columns
* Late filtering
* Unnecessary joins
* Broadcast opportunities

Flag:

```python
df1.crossJoin(df2)
```

unless explicitly justified.

Also investigate:

```python
df1.join(df2)
```

when no join condition is specified.

---

# 19. Broadcast Joins

Review:

```python
broadcast(df)
```

Check whether the broadcast DataFrame is genuinely small enough.

Do not blindly recommend broadcast joins.

Consider:

* Dataset size
* Memory
* Number of executors
* Join frequency
* Spark statistics
* AQE

---

# 20. Predicate Pushdown

Check whether filters are applied early.

Prefer:

```python
orders = (
    spark.read.table("orders")
    .filter(F.col("order_date") >= start_date)
    .select(
        "order_id",
        "customer_id",
        "amount"
    )
)
```

Look for:

* Late filtering
* Reading unnecessary columns
* `select("*")`
* Processing unnecessary rows

---

# 21. Python UDF

Identify:

```python
@udf
```

and:

```python
F.udf(...)
```

Prefer native Spark functions where possible.

Example:

```python
# Avoid when native Spark functionality exists

@F.udf
def normalize(value):
    return value.lower()
```

Prefer:

```python
df = df.withColumn(
    "normalized",
    F.lower(F.col("value"))
)
```

Python UDFs can introduce serialization and execution overhead.

---

# 22. Pandas UDF

Review:

```python
@pandas_udf
```

Check whether a native Spark implementation exists.

Consider:

* Serialization
* Memory consumption
* Batch size
* Dataset size
* Native Spark alternatives

Do not automatically reject Pandas UDFs.

---

# 23. Window Functions

Review:

```python
Window.partitionBy(...)
Window.orderBy(...)
```

Check for:

* Global windows
* Large unbounded windows
* Expensive ordering
* Missing partitioning
* Repeated window calculations

Example concern:

```python
Window.orderBy("timestamp")
```

without partitioning can require expensive global processing.

---

# 24. DataFrame Width

Look for:

```python
select("*")
```

and unnecessary columns carried through transformations.

Prefer selecting only required columns.

This reduces:

* Network transfer
* Shuffle size
* Memory consumption
* Serialization
* Storage

---

# 25. Delta Lake

When Delta tables are used, review:

* MERGE conditions
* Duplicate MERGE matches
* Schema evolution
* Small files
* Partitioning
* Liquid Clustering
* Z-ORDER
* OPTIMIZE
* VACUUM
* Change Data Feed
* Deletion Vectors

Do not recommend partitioning, Z-ORDER, or Liquid Clustering without understanding the workload.

---

# 26. MERGE

Review:

```python
target.alias("t").merge(
    source.alias("s"),
    "t.id = s.id"
)
```

Check:

* Correct matching keys
* Duplicate source keys
* Unnecessary updates
* Large target scans
* Predicate pruning
* Correct insert/update/delete behavior

Identify possible correctness issues before performance issues.

---

# 27. Small Files

Look for code that can generate excessive small files.

Examples:

```python
df.repartition(10000).write...
```

and:

```python
df.coalesce(1).write...
```

Consider:

* Input size
* Output partition count
* Write frequency
* File size
* Batch vs streaming

Do not prescribe arbitrary partition counts.

---

# 28. Structured Streaming

Check:

* Checkpoint location
* Watermarks
* Trigger configuration
* State growth
* Stream-stream joins
* foreachBatch
* Idempotency
* Schema evolution
* Auto Loader
* Stateful aggregations

Flag potentially unbounded state.

Example:

```python
stream_df.groupBy("customer_id").count()
```

without appropriate state management may require investigation.

---

# 29. Auto Loader

When ingesting files, check whether Auto Loader is appropriate.

Review:

```python
.format("cloudFiles")
```

Check:

* Schema management
* Checkpointing
* Schema evolution
* Trigger configuration
* File notification strategy where relevant

Do not recommend Auto Loader for every batch ingestion workload.

---

# 30. SQL Review

Check Spark SQL for:

* `SELECT *`
* unnecessary `DISTINCT`
* unnecessary `ORDER BY`
* Cartesian joins
* inefficient subqueries
* repeated computation
* unnecessary scans
* late filters
* excessive aggregation

---

# 31. Security

Search for:

* Passwords
* API keys
* Tokens
* Connection strings
* Cloud credentials
* Hardcoded secrets
* Sensitive information

Never expose detected secrets in the review output.

Instead say:

> Hardcoded credential detected. Remove it and use the approved secret-management mechanism.

Example:

```python
token = dbutils.secrets.get(
    scope="my-scope",
    key="api-token"
)
```

---

# 32. Hardcoded Paths

Review:

```python
spark.read.load(
    "/mnt/production/customer/"
)
```

Check whether paths should be configuration-driven or use Unity Catalog tables/volumes.

Prefer:

```python
spark.read.table(
    "prod.customer.customer"
)
```

when appropriate.

Do not automatically flag all hardcoded paths.

---

# 33. Unity Catalog

Check:

* Catalog/schema/table references
* Hardcoded storage paths
* Permissions
* Secrets
* External locations
* Volumes
* Governance

Prefer governed Unity Catalog objects over direct storage access when applicable.

---

# 34. Databricks Serverless

Check whether code contains assumptions incompatible with Serverless.

Review:

* Unsupported Spark configurations
* Cluster-specific dependencies
* Init scripts
* Local filesystem assumptions
* Library installation assumptions
* Driver/executor assumptions

Do not claim something is unsupported unless there is clear evidence.

---

# 35. Photon

Identify workloads where Photon may provide benefit.

Do not automatically recommend:

> Enable Photon.

Instead explain why Photon may or may not help based on the workload.

---

# 36. Cost Review

Look for patterns that unnecessarily increase compute:

* Full-table scans
* Repeated actions
* Unnecessary shuffles
* Excessive repartition
* Excessive caching
* Large driver operations
* Repeated joins
* Unnecessary recomputation
* Poor filtering
* Excessive output files

When possible, explain the cost mechanism rather than making unsupported cost estimates.

---

# 37. Correctness

Prioritize correctness over optimization.

Check for:

* Incorrect joins
* Duplicate records
* Incorrect aggregation
* Null handling
* Incorrect date/time logic
* Schema assumptions
* Missing deduplication
* Incorrect MERGE conditions
* Incorrect streaming semantics
* Race conditions

Do not recommend a performance optimization that changes business behavior.

---

# 38. Finding Format

For every finding use exactly:

| Issue | Severity | Recommendation | Example Fix |
| ----- | -------- | -------------- | ----------- |

Example:

| Issue                                                                  | Severity | Recommendation                                                             | Example Fix                                                   |
| ---------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `collect()` retrieves potentially large distributed data to the driver | High     | Keep processing distributed or explicitly bound the data before collecting | `df.filter(F.col("status") == "ACTIVE").limit(100).collect()` |

The `Example Fix` must contain a concrete corrected code example whenever a practical fix exists.

Use PySpark syntax where the finding relates to PySpark.

---

# 39. Finding Evidence

For each finding, identify the relevant:

* File
* Notebook
* Cell, when available
* Line number, when available
* Code pattern

Example:

```text
File: notebooks/customer_ingestion.py
Line: 42
Pattern: df.collect()
```

If line information is unavailable, do not invent it.

---

# 40. Avoid False Positives

Before reporting a finding, ask:

1. Is the pattern actually present?
2. Is it relevant to the workload?
3. Is it potentially harmful?
4. Is there enough evidence?
5. Could the pattern be intentional?
6. Is the severity justified?

If context is insufficient, state the uncertainty.

Do not invent:

* Runtime behavior
* Dataset size
* Cluster size
* Cost savings
* Execution plans
* Performance improvements

---

# 41. Review Summary

After findings, provide:

## Review Summary

* Overall assessment
* Number of findings
* Critical findings
* High findings
* Medium findings
* Low findings

## Top Priorities

List the three most important changes.

## Performance Risks

Summarize Spark/Databricks performance concerns.

## Code Quality

Summarize maintainability concerns.

## Security

Summarize security concerns.

## Databricks Recommendations

Summarize applicable Databricks-specific recommendations.

---

# 42. Overall Assessment

Use one of:

* Excellent
* Good
* Needs Improvement
* Significant Issues
* Critical Issues

Base the assessment on the actual findings.

Do not assign a numeric score unless explicitly requested.

---

# 43. Review Principles

Always:

* Understand before optimizing.
* Prefer evidence over assumptions.
* Prioritize correctness.
* Avoid false positives.
* Explain why something is a problem.
* Provide actionable recommendations.
* Provide corrected code examples.
* Consider Databricks execution behavior.
* Consider performance and cost.
* Consider production operational impact.

Never:

* Recommend `repartition()` blindly.
* Recommend `cache()` blindly.
* Recommend `broadcast()` blindly.
* Recommend `coalesce(1)` for convenience.
* Treat every `display()` as a defect.
* Treat every UDF as a defect.
* Invent performance numbers.
* Invent line numbers.
* Expose secrets found during review.
