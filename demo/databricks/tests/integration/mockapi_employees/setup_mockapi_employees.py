"""
Integration Test — mockapi_employees — Setup

Builds synthetic staging-layer DataFrames, runs the full transformation chain
(staging → enriched → curated), and exposes _result for the validate script.

Coverage manifest (printed only):
  raw_ingestion : EXCLUDED    — uses dbutils.fs.mkdirs / dbutils.fs.put (cannot run locally)
  staging       : CONTROLLED  — apply_staging_transform exercised with 4 synthetic rows
  enriched      : CONTROLLED  — type casts, 8 derived cols, null normalisation, dedup
  curated       : CONTROLLED  — select of enriched attributes
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../..")))

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    BooleanType, DateType, DoubleType, IntegerType,
    StringType, StructField, StructType, TimestampType,
)
from pyspark.sql.functions import col, expr, when

from pltdata import (
    Attribute, AttrType, Entity, EntityProperty, EntityType,
    Layer, Parameter, RetentionDuration,
)

# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------
spark = (
    SparkSession.builder
    .master("local[1]")
    .appName("integration-test-mockapi_employees-setup")
    .config("spark.sql.shuffle.partitions", "1")
    .getOrCreate()
)

print("[START] setup_mockapi_employees | mode=controlled | scope=staging,enriched,curated")

coverage = {
    "raw_ingestion": {"disposition": "EXCLUDED",   "reason": "uses dbutils.fs — cannot run locally"},
    "staging":       {"disposition": "CONTROLLED", "entities": ["employees"]},
    "enriched":      {"disposition": "CONTROLLED", "entities": ["mockapi_employees"]},
    "curated":       {"disposition": "CONTROLLED", "entities": ["employee_profile"]},
}
print(f"[INFO] Coverage: {coverage}")

# ---------------------------------------------------------------------------
# Entity definitions — verbatim from source notebooks
# ---------------------------------------------------------------------------

_mockapi_employees_staging = Entity(
    entity_name="employees",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="staging/cq/mockapi/int/employees",
    source=["raw/cq/mockapi/int/employees"],
    layer=Layer.STAGING,
    product="cq",
    version="1.0.0",
    source_system="mockapi",
    is_public=False,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[
        Attribute(name="employee_id",     attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/employee_id"]),
        Attribute(name="first_name",      attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/first_name"],
                  parameter=[Parameter(name="pii", value="first_name")]),
        Attribute(name="last_name",       attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/last_name"],
                  parameter=[Parameter(name="pii", value="last_name")]),
        Attribute(name="email",           attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/email"],
                  parameter=[Parameter(name="pii", value="email")]),
        Attribute(name="phone",           attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/phone"],
                  parameter=[Parameter(name="pii", value="phone")]),
        Attribute(name="department",      attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/department"]),
        Attribute(name="job_title",       attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/job_title"]),
        Attribute(name="salary",          attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/salary"],
                  parameter=[Parameter(name="pii", value="salary")]),
        Attribute(name="hire_date",       attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/hire_date"]),
        Attribute(name="manager_id",      attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/manager_id"]),
        Attribute(name="office_location", attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/office_location"]),
        Attribute(name="status",          attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/status"]),
        Attribute(name="created_at",      attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/created_at"]),
        Attribute(name="updated_at",      attr_type=AttrType.STRING,
                  source=["raw/cq/mockapi/int/employees/updated_at"]),
        Attribute(name="UploadDate",      attr_type=AttrType.TIMESTAMP),
    ],
)

_mockapi_employees_enriched = Entity(
    entity_name="mockapi_employees",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="enriched/cq/int/mockapi/employees",
    source=["staging/cq/mockapi/int/employees"],
    layer=Layer.ENRICHED,
    product="cq",
    version="1.0.0",
    source_system="mockapi",
    is_public=True,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    retention_duration=RetentionDuration(dev=None, qua=None, prd=None),
    attributes=[
        Attribute(name="employee_id",     attr_type=AttrType.STRING, is_key=True,
                  source=["staging/cq/mockapi/int/employees/employee_id"]),
        Attribute(name="first_name",      attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/first_name"],
                  parameter=[Parameter(name="pii", value="first_name")]),
        Attribute(name="last_name",       attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/last_name"],
                  parameter=[Parameter(name="pii", value="last_name")]),
        Attribute(name="email",           attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/email"],
                  parameter=[Parameter(name="pii", value="email")]),
        Attribute(name="phone",           attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/phone"],
                  parameter=[Parameter(name="pii", value="phone")]),
        Attribute(name="department",      attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/department"]),
        Attribute(name="job_title",       attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/job_title"]),
        Attribute(name="salary",          attr_type=AttrType.DOUBLE,
                  source=["staging/cq/mockapi/int/employees/salary"],
                  parameter=[Parameter(name="pii", value="salary")]),
        Attribute(name="hire_date",       attr_type=AttrType.DATE,
                  source=["staging/cq/mockapi/int/employees/hire_date"]),
        Attribute(name="manager_id",      attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/manager_id"]),
        Attribute(name="office_location", attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/office_location"]),
        Attribute(name="status",          attr_type=AttrType.STRING,
                  source=["staging/cq/mockapi/int/employees/status"]),
        Attribute(name="created_at",      attr_type=AttrType.TIMESTAMP,
                  source=["staging/cq/mockapi/int/employees/created_at"]),
        Attribute(name="updated_at",      attr_type=AttrType.TIMESTAMP,
                  source=["staging/cq/mockapi/int/employees/updated_at"]),
        Attribute(name="full_name",       attr_type=AttrType.STRING),
        Attribute(name="email_domain",    attr_type=AttrType.STRING),
        Attribute(name="job_level",       attr_type=AttrType.STRING),
        Attribute(name="salary_band",     attr_type=AttrType.STRING),
        Attribute(name="tenure_days",     attr_type=AttrType.INT),
        Attribute(name="tenure_years",    attr_type=AttrType.INT),
        Attribute(name="has_manager",     attr_type=AttrType.BOOLEAN),
        Attribute(name="is_active",       attr_type=AttrType.BOOLEAN),
        Attribute(name="is_valid_email",  attr_type=AttrType.BOOLEAN),
    ],
)

_employee_profile_curated = Entity(
    entity_name="employee_profile",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="curated/cq/employee360/employee_profile",
    layer=Layer.CURATED,
    product="cq",
    version="1.0.0",
    source_system="mockapi",
    is_public=True,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    retention_duration=RetentionDuration(dev=None, qua=None, prd=None),
    attributes=[
        Attribute(name="employee_id",    attr_type=AttrType.STRING, is_key=True),
        Attribute(name="full_name",      attr_type=AttrType.STRING,
                  parameter=[Parameter(name="pii", value="full_name")]),
        Attribute(name="email",          attr_type=AttrType.STRING,
                  parameter=[Parameter(name="pii", value="email")]),
        Attribute(name="phone",          attr_type=AttrType.STRING,
                  parameter=[Parameter(name="pii", value="phone")]),
        Attribute(name="department",     attr_type=AttrType.STRING),
        Attribute(name="job_title",      attr_type=AttrType.STRING),
        Attribute(name="job_level",      attr_type=AttrType.STRING),
        Attribute(name="salary_band",    attr_type=AttrType.STRING),
        Attribute(name="office_location",attr_type=AttrType.STRING),
        Attribute(name="tenure_years",   attr_type=AttrType.INT),
        Attribute(name="is_active",      attr_type=AttrType.BOOLEAN),
        Attribute(name="has_manager",    attr_type=AttrType.BOOLEAN),
        Attribute(name="email_domain",   attr_type=AttrType.STRING),
        Attribute(name="hire_date",      attr_type=AttrType.DATE),
        Attribute(name="created_at",     attr_type=AttrType.TIMESTAMP),
        Attribute(name="updated_at",     attr_type=AttrType.TIMESTAMP),
    ],
)

# ---------------------------------------------------------------------------
# Transformation functions — extracted from source notebooks
# ---------------------------------------------------------------------------

_STAGING_ATTRS = _mockapi_employees_staging.attributes
_UPLOAD_DATE_FMT = "yyyy-MM-dd HH:mm:ss.SSSSSSS"


def apply_staging_transform(source_df, upload_date_str="2024-01-01 00:00:00.0000000"):
    result = source_df.withColumn(
        "UploadDate",
        F.to_timestamp(F.lit(upload_date_str), _UPLOAD_DATE_FMT),
    )
    for attr in _STAGING_ATTRS:
        source_locator = (
            attr.name if attr.source is None or len(attr.source) == 0
            else attr.source[0]
        )
        source_name = source_locator.split("/")[-1]
        if source_name == attr.name and source_name in result.columns:
            continue
        elif source_name in result.columns:
            result = result.withColumnRenamed(source_name, attr.name)
    keep = {a.name for a in _STAGING_ATTRS}
    for c in result.columns:
        if c not in keep:
            result = result.drop(c)
    return result


def apply_enriched_transform(staging_df):
    transformed = staging_df.select(
        F.col("employee_id").cast("string").alias("employee_id"),
        F.col("first_name").cast("string").alias("first_name"),
        F.col("last_name").cast("string").alias("last_name"),
        F.col("email").cast("string").alias("email"),
        F.col("phone").cast("string").alias("phone"),
        F.col("department").cast("string").alias("department"),
        F.col("job_title").cast("string").alias("job_title"),
        F.col("salary").cast(DoubleType()).alias("salary"),
        F.col("hire_date").cast(DateType()).alias("hire_date"),
        F.col("manager_id").cast("string").alias("manager_id"),
        F.col("office_location").cast("string").alias("office_location"),
        F.col("status").cast("string").alias("status"),
        F.col("created_at").cast(TimestampType()).alias("created_at"),
        F.col("updated_at").cast(TimestampType()).alias("updated_at"),
    )
    transformed = (
        transformed
        .withColumn("full_name", F.concat_ws(" ", F.col("first_name"), F.col("last_name")))
        .withColumn("email_domain", F.split(F.col("email"), "@").getItem(1))
        .withColumn(
            "job_level",
            F.when(F.lower(F.col("job_title")).rlike("senior|lead|head"), "Senior")
             .otherwise("Standard")
        )
        .withColumn(
            "salary_band",
            F.when(F.col("salary") < 50000, "Band 1")
             .when(F.col("salary") < 80000, "Band 2")
             .when(F.col("salary") < 120000, "Band 3")
             .otherwise("Band 4")
        )
        .withColumn("tenure_days", F.datediff(F.current_date(), F.col("hire_date")).cast(IntegerType()))
        .withColumn("tenure_years", F.floor(F.col("tenure_days") / 365).cast(IntegerType()))
        .withColumn("has_manager", F.col("manager_id").isNotNull())
        .withColumn("is_active", F.col("status") == "active")
        .withColumn("is_valid_email", F.col("email").rlike(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"))
    )
    # Null normalisation (verbatim from source notebook)
    for column in transformed.columns:
        transformed = transformed.withColumn(
            column,
            when((col(column) == "nan") | (col(column) == "null"), None).otherwise(col(column))
        )
    # Deduplication
    bk_names = [a.name for a in _mockapi_employees_enriched.attributes if a.is_key]
    target = transformed.withColumn(
        "rn",
        expr(f"ROW_NUMBER() OVER (PARTITION BY ({','.join(bk_names)}) ORDER BY updated_at DESC)")
    )
    return target.where("rn=1").drop("rn")


def apply_curated_transform(enriched_df):
    return enriched_df.select([a.name for a in _employee_profile_curated.attributes])


# ---------------------------------------------------------------------------
# Synthetic staging input — all 14 base columns as STRING, UploadDate added
# ---------------------------------------------------------------------------

_RAW_SCHEMA = StructType([
    StructField("employee_id",      StringType(), True),
    StructField("first_name",       StringType(), True),
    StructField("last_name",        StringType(), True),
    StructField("email",            StringType(), True),
    StructField("phone",            StringType(), True),
    StructField("department",       StringType(), True),
    StructField("job_title",        StringType(), True),
    StructField("salary",           StringType(), True),
    StructField("hire_date",        StringType(), True),
    StructField("manager_id",       StringType(), True),
    StructField("office_location",  StringType(), True),
    StructField("status",           StringType(), True),
    StructField("created_at",       StringType(), True),
    StructField("updated_at",       StringType(), True),
])

# Reserved test keys — must not collide with production data
_KEY_001 = "INT_TEST_001"   # active Senior Engineer with manager
_KEY_002 = "INT_TEST_002"   # inactive Recruiter without manager
_KEY_003 = "INT_TEST_003"   # deduplication — two rows, newer updated_at must survive

_source_rows = [
    # INT_TEST_001 — active Senior Engineer
    (_KEY_001, "Test", "Senior",   "test.senior@mockapi.io",   "+1-555-0000001",
     "Engineering", "Senior Engineer", "85000.0", "2020-01-01",
     "MGR_TEST_001", "London",  "active",   "2020-01-01T00:00:00", "2024-01-01T00:00:00"),
    # INT_TEST_002 — inactive Recruiter, no manager
    (_KEY_002, "Test", "Standard", "test.standard@mockapi.io", "+1-555-0000002",
     "HR",          "Recruiter",       "48000.0", "2022-06-01",
     None,          "Paris",   "inactive", "2022-06-01T00:00:00", "2024-01-01T00:00:00"),
    # INT_TEST_003 — OLDER row (must be dropped by dedup)
    (_KEY_003, "Dedup", "Loser",  "dedup.loser@mockapi.io",   "+1-555-0000003",
     "Finance",     "Analyst",         "60000.0", "2021-01-01",
     "MGR_TEST_001", "Toronto", "active",   "2021-01-01T00:00:00", "2023-01-01T00:00:00"),
    # INT_TEST_003 — NEWER row (must survive dedup)
    (_KEY_003, "Dedup", "Winner", "dedup.winner@mockapi.io",  "+1-555-0000004",
     "Finance",     "Lead Analyst",    "75000.0", "2021-01-01",
     "MGR_TEST_001", "Sydney",  "active",   "2021-01-01T00:00:00", "2024-06-01T00:00:00"),
]

raw_df = spark.createDataFrame(_source_rows, schema=_RAW_SCHEMA)

# ---------------------------------------------------------------------------
# Run the transformation chain
# ---------------------------------------------------------------------------

staging_df  = apply_staging_transform(raw_df, upload_date_str="2024-01-01 00:00:00.0000000")
enriched_df = apply_enriched_transform(staging_df)
curated_df  = apply_curated_transform(enriched_df)


# ---------------------------------------------------------------------------
# Collect scenario results
# ---------------------------------------------------------------------------

def _collect_one(key: str, label: str) -> dict:
    rows = curated_df.filter(F.col("employee_id") == key).collect()
    assert rows, f"[FAIL] scenario={label!r} | no curated row for key={key!r}"
    row = rows[0]
    return {
        "disposition": "CONTROLLED",
        "key": {"employee_id": key},
        "actual": {
            "full_name":      row.full_name,
            "salary_band":    row.salary_band,
            "job_level":      row.job_level,
            "has_manager":    row.has_manager,
            "is_active":      row.is_active,
            "email_domain":   row.email_domain,
            "office_location": row.office_location,
        },
    }


def scenario_active_employee_with_manager() -> dict:
    return _collect_one(_KEY_001, "active_employee_with_manager")


def scenario_inactive_employee_without_manager() -> dict:
    return _collect_one(_KEY_002, "inactive_employee_without_manager")


def scenario_deduplication() -> dict:
    dedup_rows = curated_df.filter(F.col("employee_id") == _KEY_003).collect()
    assert len(dedup_rows) == 1, (
        f"[FAIL] scenario=deduplication | expected 1 curated row for key={_KEY_003!r}, "
        f"got {len(dedup_rows)}"
    )
    row = dedup_rows[0]
    return {
        "disposition": "CONTROLLED",
        "key": {"employee_id": _KEY_003},
        "actual": {
            "row_count":      1,
            "last_name":      row.last_name,
            "job_level":      row.job_level,
            "office_location": row.office_location,
        },
    }


scenarios = {
    "active_employee_with_manager":      scenario_active_employee_with_manager(),
    "inactive_employee_without_manager": scenario_inactive_employee_without_manager(),
    "deduplication":                     scenario_deduplication(),
}

_result = {
    "initiative": "mockapi_employees",
    "mode": "controlled_test_data",
    "scenarios": scenarios,
}

print(f"[OK] setup_mockapi_employees — scenarios: {list(scenarios.keys())}")
