# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC Enriched job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               ENRICHED
# MAGIC * Entity:              mockapi_employees
# MAGIC ### Notebook information
# MAGIC
# MAGIC Load staged data into enriched object

# COMMAND ----------

# MAGIC %run "../../_platform_app/plt_init"

# COMMAND ----------

# DBTITLE 1,Entity Definition
mockapi_employees_enriched = Entity(
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
        Attribute(
            name="employee_id",
            attr_type=AttrType.STRING,
            is_key=True,
            source=["staging/cq/mockapi/int/employees/employee_id"],
        ),
        Attribute(
            name="first_name",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/first_name"],
            parameter=[Parameter(name="pii", value="first_name")],
        ),
        Attribute(
            name="last_name",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/last_name"],
            parameter=[Parameter(name="pii", value="last_name")],
        ),
        Attribute(
            name="email",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/email"],
            parameter=[Parameter(name="pii", value="email")],
        ),
        Attribute(
            name="phone",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/phone"],
            parameter=[Parameter(name="pii", value="phone")],
        ),
        Attribute(
            name="department",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/department"],
        ),
        Attribute(
            name="job_title",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/job_title"],
        ),
        Attribute(
            name="salary",
            attr_type=AttrType.DOUBLE,
            source=["staging/cq/mockapi/int/employees/salary"],
            parameter=[Parameter(name="pii", value="salary")],
        ),
        Attribute(
            name="hire_date",
            attr_type=AttrType.DATE,
            source=["staging/cq/mockapi/int/employees/hire_date"],
        ),
        Attribute(
            name="manager_id",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/manager_id"],
        ),
        Attribute(
            name="office_location",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/office_location"],
        ),
        Attribute(
            name="status",
            attr_type=AttrType.STRING,
            source=["staging/cq/mockapi/int/employees/status"],
        ),
        Attribute(
            name="created_at",
            attr_type=AttrType.TIMESTAMP,
            source=["staging/cq/mockapi/int/employees/created_at"],
        ),
        Attribute(
            name="updated_at",
            attr_type=AttrType.TIMESTAMP,
            source=["staging/cq/mockapi/int/employees/updated_at"],
        ),
        Attribute(name="full_name", attr_type=AttrType.STRING),
        Attribute(name="email_domain", attr_type=AttrType.STRING),
        Attribute(name="job_level", attr_type=AttrType.STRING),
        Attribute(name="salary_band", attr_type=AttrType.STRING),
        Attribute(name="tenure_days", attr_type=AttrType.INT),
        Attribute(name="tenure_years", attr_type=AttrType.INT),
        Attribute(name="has_manager", attr_type=AttrType.BOOLEAN),
        Attribute(name="is_active", attr_type=AttrType.BOOLEAN),
        Attribute(name="is_valid_email", attr_type=AttrType.BOOLEAN),
    ],
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(mockapi_employees_enriched)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=mockapi_employees_enriched, enforce_schema=True),
    target_persist=True,
    target_merge_type=TargetMergeType.MERGE_ON_PRIMARY_KEY,
    lifecycle_handler=EnrichedIngestionLifecycleHandler(
        ["staging/cq/mockapi/int/employees"],
        mockapi_employees_enriched.entity_locator,
        True
    ),
    increment_driver_source_entity_name="mockapi_employees",
    source_employees_staging=Drl.from_config(
        entity_name="employees",
        product="cq",
        module="int",
        layer=Layer.STAGING,
        source_system="mockapi"
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Data transformation

# COMMAND ----------

# DBTITLE 1,Transform
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, DateType, TimestampType, IntegerType

transformed_plt = source_employees_staging.select(
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

# Derived columns
transformed_plt = (
    transformed_plt
    .withColumn("full_name", F.concat_ws(" ", F.col("first_name"), F.col("last_name")))
    .withColumn("email_domain", F.split(F.col("email"), "@").getItem(1))
    .withColumn(
        "job_level",
        F.when(
            F.lower(F.col("job_title")).rlike("senior|lead|head"), "Senior"
        ).otherwise("Standard")
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
    .withColumn(
        "is_valid_email",
        F.col("email").rlike(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    )
)

# COMMAND ----------

# DBTITLE 1,Null normalisation
from pyspark.sql.functions import col, when

for column in transformed_plt.columns:
    transformed_plt = transformed_plt.withColumn(
        column,
        when((col(column) == "nan") | (col(column) == "null"), None).otherwise(col(column))
    )

# COMMAND ----------

# DBTITLE 1,Deduplication
from pyspark.sql.functions import expr

bkList = [a for a in mockapi_employees_enriched.attributes if a.is_key]
if len(bkList) > 0:
    target = transformed_plt.withColumn(
        "rn",
        expr(f"ROW_NUMBER() OVER (PARTITION BY ({','.join([bk.name for bk in bkList])}) ORDER BY updated_at DESC)")
    )
    target = target.where("rn=1").drop("rn")

# COMMAND ----------

# DBTITLE 1,End Transform
plt_transform.end_transform(target)
