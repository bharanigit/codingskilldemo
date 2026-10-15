"""
Unit tests for: demo/databricks/3-staging/mockapi/transform_employees.py

Transformation under test:
  Per-file staging transform that adds UploadDate, renames columns whose
  DRL source path differs from the attribute name, and drops any columns
  absent from the staging entity definition.

Source notebook read directly — no compiled artifact required.
"""
import os

import pytest
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

from pltdata import (
    Attribute,
    AttrType,
    Entity,
    EntityProperty,
    EntityType,
    Layer,
    Parameter,
)

# ---------------------------------------------------------------------------
# Entity definitions — verbatim from source notebook
# ---------------------------------------------------------------------------

_mockapi_employees_raw = Entity(
    entity_name="employees",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="raw/cq/mockapi/int/employees",
    source=[],
    layer=Layer.RAW,
    product="cq",
    version="1.0.0",
    source_system="mockapi",
    is_public=False,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[
        Attribute(name="employee_id",      attr_type=AttrType.STRING),
        Attribute(name="first_name",       attr_type=AttrType.STRING),
        Attribute(name="last_name",        attr_type=AttrType.STRING),
        Attribute(name="email",            attr_type=AttrType.STRING,
                  parameter=[Parameter(name="pii", value="email")]),
        Attribute(name="phone",            attr_type=AttrType.STRING,
                  parameter=[Parameter(name="pii", value="phone")]),
        Attribute(name="department",       attr_type=AttrType.STRING),
        Attribute(name="job_title",        attr_type=AttrType.STRING),
        Attribute(name="salary",           attr_type=AttrType.DOUBLE,
                  parameter=[Parameter(name="pii", value="salary")]),
        Attribute(name="hire_date",        attr_type=AttrType.DATE),
        Attribute(name="manager_id",       attr_type=AttrType.STRING),
        Attribute(name="office_location",  attr_type=AttrType.STRING),
        Attribute(name="status",           attr_type=AttrType.STRING),
        Attribute(name="created_at",       attr_type=AttrType.TIMESTAMP),
        Attribute(name="updated_at",       attr_type=AttrType.TIMESTAMP),
    ],
)

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

# ---------------------------------------------------------------------------
# Standalone transformation — extracted from the notebook's per-file loop body
# ---------------------------------------------------------------------------

_UPLOAD_DATE_FMT = "yyyy-MM-dd HH:mm:ss.SSSSSSS"
_STAGING_ATTRS = _mockapi_employees_staging.attributes


def apply_staging_transform(source_df, upload_date_str="2024-01-01 00:00:00.0000000"):
    """
    Replicates one iteration of the notebook's uploaded-file loop:
      1. Add UploadDate as a timestamp column.
      2. Rename columns whose DRL source name differs from the attribute name.
      3. Drop columns not declared in the staging entity.
    """
    result = source_df.withColumn(
        "UploadDate",
        F.to_timestamp(F.lit(upload_date_str), _UPLOAD_DATE_FMT),
    )

    for attr in _STAGING_ATTRS:
        source_locator = (
            attr.name
            if attr.source is None or len(attr.source) == 0
            else attr.source[0]
        )
        source_name = source_locator.split("/")[-1]
        if source_name == attr.name and source_name in result.columns:
            continue
        elif source_name in result.columns:
            result = result.withColumnRenamed(source_name, attr.name)

    keep = {a.name for a in _STAGING_ATTRS}
    for col in result.columns:
        if col not in keep:
            result = result.drop(col)

    return result


# ---------------------------------------------------------------------------
# Source schema — all StringType (CSV round-trip; staging does not cast types)
# ---------------------------------------------------------------------------

_RAW_SOURCE_SCHEMA = StructType([
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

_FIXTURE_CSV = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../../data/raw/mockapi/mockapi_employees.csv")
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def source_df(spark):
    return spark.read.csv(_FIXTURE_CSV, header=True, schema=_RAW_SOURCE_SCHEMA)


@pytest.fixture(scope="module")
def transformed_df(source_df):
    return apply_staging_transform(source_df, upload_date_str="2024-01-01 00:00:00.0000000")


@pytest.fixture(scope="module")
def transformed_rows(transformed_df):
    return {row.employee_id: row for row in transformed_df.collect()}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_EXPECTED_COLUMNS = {a.name for a in _STAGING_ATTRS}


def test_output_has_exactly_staging_entity_columns(transformed_df):
    """Output column set matches the staging entity attribute names exactly."""
    assert set(transformed_df.columns) == _EXPECTED_COLUMNS


def test_upload_date_is_timestamp_type(transformed_df):
    """UploadDate must be TimestampType — it is added by this transform, not inherited from raw."""
    field_map = {f.name: f for f in transformed_df.schema.fields}
    assert "UploadDate" in field_map
    assert isinstance(field_map["UploadDate"].dataType, TimestampType)


def test_upload_date_populated_for_all_rows(transformed_rows):
    """Every output row carries a non-null UploadDate."""
    for emp_id, row in transformed_rows.items():
        assert row.UploadDate is not None, f"UploadDate is null for employee_id={emp_id!r}"


def test_string_fields_pass_through_unchanged(transformed_rows):
    """Fields with matching source names are not modified by the transform."""
    row = transformed_rows["UNIT_001"]
    assert row.first_name == "Alice"
    assert row.last_name == "Smith"
    assert row.department == "Engineering"
    assert row.job_title == "Software Engineer"
    assert row.office_location == "London"
    assert row.status == "active"


def test_inactive_employee_is_retained(transformed_rows):
    """The staging transform does not filter rows — all source records pass through."""
    assert "UNIT_002" in transformed_rows
    assert transformed_rows["UNIT_002"].status == "inactive"


def test_nullable_manager_id_passes_through(transformed_rows):
    """Rows where manager_id is absent in the source survive the transform as null."""
    row = transformed_rows["UNIT_002"]
    assert row.manager_id is None


def test_extra_source_column_is_dropped(spark):
    """A column present in the raw DataFrame but absent from the staging entity is dropped."""
    extra_schema = _RAW_SOURCE_SCHEMA.add(StructField("unexpected_col", StringType(), True))
    raw_with_extra = spark.createDataFrame(
        [(
            "UNIT_X", "Carol", "Lee", "carol@mockapi.io", "+1-555-0000000",
            "Finance", "Analyst", "60000", "2022-01-01", None,
            "Toronto", "active", "2022-01-01T00:00:00", "2024-01-01T00:00:00",
            "should_be_dropped",
        )],
        schema=extra_schema,
    )
    result = apply_staging_transform(raw_with_extra)
    assert "unexpected_col" not in result.columns
    assert set(result.columns) == _EXPECTED_COLUMNS
