# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC Staging job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               STAGING
# MAGIC * Entity:              customers
# MAGIC ### Notebook information
# MAGIC
# MAGIC Uses Platform Development Framework

# COMMAND ----------

# MAGIC %run "../../_platform_app/plt_init"

# COMMAND ----------

# DBTITLE 1,Entity Definition
customers_raw = Entity(
    entity_name="customers",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="raw/crm/customers/int/customers",
    source=[],
    layer=Layer.RAW,
    product="demo",
    version="1.0.0",
    source_system="crm",
    is_public=False,
    parameter=[],
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[],
)

customers_staging = Entity(
    entity_name="customers",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="staging/crm/customers/int/customers",
    source=[customers_raw],
    layer=Layer.STAGING,
    product="demo",
    version="1.0.0",
    source_system="crm",
    is_public=False,
    parameter=[],
    entity_property=EntityProperty(
        auto_compute_hash=True,
        auto_compute_loadinfo=True,
    ),
    attributes=[
        Attribute(
            name="customer_id",
            display_name="Customer ID",
            description="Unique customer identifier (business key)",
            is_key=True,
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="first_name",
            display_name="First Name",
            description="Customer first name — standardised to title case",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="last_name",
            display_name="Last Name",
            description="Customer last name — standardised to title case",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="email",
            display_name="Email Address",
            description="Normalised lowercase email address",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="email")],
        ),
        Attribute(
            name="phone",
            display_name="Phone Number",
            description="Normalised E.164 phone number",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="phone")],
        ),
        Attribute(
            name="country_code",
            display_name="Country Code",
            description="ISO 3166-1 alpha-2 country code",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="created_at",
            display_name="Created At",
            description="Original creation timestamp from source",
            attr_type=AttrType.TIMESTAMP,
        ),
        Attribute(
            name="updated_at",
            display_name="Updated At",
            description="Last update timestamp from source",
            attr_type=AttrType.TIMESTAMP,
        ),
        Attribute(
            name="is_valid_email",
            display_name="Is Valid Email",
            description="True when email passes format validation",
            attr_type=AttrType.BOOLEAN,
        ),
    ],
    retention_duration=RetentionDuration(dev=30, qua=90, prd=None),
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(customers_staging)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=customers_staging, enforce_schema=True),
    increment_driver_source_entity_name="customers",
)

# COMMAND ----------

# DBTITLE 1,Transform
# TODO: Implement staging transformation logic.
#
# from pyspark.sql import functions as F
#
# source_df = plt_transform.read_source(customers_raw)   # reads from raw layer
#
# target = source_df.select(
#     F.col("customer_id"),
#     F.initcap(F.col("first_name")).alias("first_name"),
#     F.initcap(F.col("last_name")).alias("last_name"),
#     F.lower(F.col("email")).alias("email"),
#     F.col("phone"),
#     F.upper(F.col("country_code")).alias("country_code"),
#     F.col("created_at"),
#     F.col("updated_at"),
#     F.col("email").rlike(r'^[^@]+@[^@]+\.[^@]+$').alias("is_valid_email"),
# )

# COMMAND ----------

# DBTITLE 1,End Transform
target = None  # Replace None with the transformed DataFrame when ready
plt_transform.end_transform(target)
