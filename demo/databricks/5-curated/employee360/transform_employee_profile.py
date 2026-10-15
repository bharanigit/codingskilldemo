# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC # Platform Development Framework

# COMMAND ----------

# MAGIC %run "../../_platform_app/plt_init"

# COMMAND ----------

# DBTITLE 1,Entity Definition
employee_profile_curated = Entity(
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
        Attribute(
            name="employee_id",
            attr_type=AttrType.STRING,
            is_key=True,
        ),
        Attribute(
            name="full_name",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="full_name")],
        ),
        Attribute(
            name="email",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="email")],
        ),
        Attribute(
            name="phone",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="phone")],
        ),
        Attribute(name="department", attr_type=AttrType.STRING),
        Attribute(name="job_title", attr_type=AttrType.STRING),
        Attribute(name="job_level", attr_type=AttrType.STRING),
        Attribute(name="salary_band", attr_type=AttrType.STRING),
        Attribute(name="office_location", attr_type=AttrType.STRING),
        Attribute(name="tenure_years", attr_type=AttrType.INT),
        Attribute(name="is_active", attr_type=AttrType.BOOLEAN),
        Attribute(name="has_manager", attr_type=AttrType.BOOLEAN),
        Attribute(name="email_domain", attr_type=AttrType.STRING),
        Attribute(name="hire_date", attr_type=AttrType.DATE),
        Attribute(name="created_at", attr_type=AttrType.TIMESTAMP),
        Attribute(name="updated_at", attr_type=AttrType.TIMESTAMP),
    ],
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(employee_profile_curated)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=employee_profile_curated, enforce_schema=True),
    target_persist=True,
    target_merge_type=TargetMergeType.MERGE_ON_PRIMARY_KEY,
    increment_driver_source_entity_name="employee_profile",
    source_mockapi_employees_enriched=Drl.from_config(
        entity_name="mockapi_employees",
        product="cq",
        module="int",
        layer=Layer.ENRICHED,
        source_system="mockapi"
    )
)

# COMMAND ----------

# DBTITLE 1,Transform
from pyspark.sql import functions as F

target = source_mockapi_employees_enriched.select(
    [a.name for a in employee_profile_curated.attributes]
)

# COMMAND ----------

# DBTITLE 1,End Transform
plt_transform.end_transform(target)
