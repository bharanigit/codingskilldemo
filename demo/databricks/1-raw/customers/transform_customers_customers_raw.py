# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
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
    entity_property=EntityProperty(
        auto_compute_hash=True,
        auto_compute_loadinfo=True,
    ),
    attributes=[
        Attribute(
            name="customer_id",
            display_name="Customer ID",
            description="Unique identifier for the customer",
            is_key=True,
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="first_name",
            display_name="First Name",
            description="Customer first name",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="last_name",
            display_name="Last Name",
            description="Customer last name",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="email",
            display_name="Email Address",
            description="Primary email address",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="email")],
        ),
        Attribute(
            name="phone",
            display_name="Phone Number",
            description="Primary phone number",
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
            description="Timestamp when the customer record was created in the source",
            attr_type=AttrType.TIMESTAMP,
        ),
        Attribute(
            name="updated_at",
            display_name="Updated At",
            description="Timestamp of last update in the source system",
            attr_type=AttrType.TIMESTAMP,
        ),
        Attribute(
            name="source_system_audit",
            display_name="Source System Audit",
            description="Raw audit metadata from the source system",
            attr_type=None,
            struct=[
                Attribute(
                    name="batch_id",
                    display_name="Batch ID",
                    description="Source batch identifier",
                    attr_type=AttrType.STRING,
                ),
                Attribute(
                    name="extracted_at",
                    display_name="Extracted At",
                    description="Extraction timestamp",
                    attr_type=AttrType.TIMESTAMP,
                ),
            ],
        ),
    ],
    retention_duration=RetentionDuration(dev=30, qua=90, prd=None),
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(customers_raw)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=customers_raw, enforce_schema=True),
)

# COMMAND ----------

# DBTITLE 1,Read Source
# TODO: Replace with actual source read — API call, file read, or JDBC pull.
# Example pattern (batch file ingestion):
#
# environment = lake_connection.product_environment
# source_path = f"/mnt/landing/{environment}/crm/customers/"
# df = (
#     spark.read
#     .format("json")
#     .option("multiLine", True)
#     .load(source_path)
# )

# COMMAND ----------

# DBTITLE 1,Transform
# TODO: Apply raw-layer transformations.
# Raw layer should be minimal — preserve source fidelity.
# Typical steps:
#   - Cast columns to correct types
#   - Flatten any top-level nested fields
#   - Add source audit metadata
#
# target = df.select(
#     col("id").alias("customer_id"),
#     col("firstName").alias("first_name"),
#     col("lastName").alias("last_name"),
#     col("emailAddress").alias("email"),
#     col("mobilePhone").alias("phone"),
#     col("country").alias("country_code"),
#     to_timestamp(col("createdAt")).alias("created_at"),
#     to_timestamp(col("updatedAt")).alias("updated_at"),
# )

# COMMAND ----------

# DBTITLE 1,End Transform
target = None  # Replace None with the transformed DataFrame when ready
plt_transform.end_transform(target)
