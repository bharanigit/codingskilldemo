# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC Enriched job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               ENRICHED
# MAGIC * Entity:              customers
# MAGIC ### Notebook information
# MAGIC
# MAGIC Uses Platform Development Framework

# COMMAND ----------

# MAGIC %run "../../_platform_app/plt_init"

# COMMAND ----------

# DBTITLE 1,Entity Definition

# Source — staging entity (read from staging layer)
customers_staging = Entity(
    entity_name="customers",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="staging/crm/customers/int/customers",
    source=[],
    layer=Layer.STAGING,
    product="demo",
    version="1.0.0",
    source_system="crm",
    is_public=False,
    parameter=[],
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[],
)

# Target — enriched entity
customers_enriched = Entity(
    entity_name="customers",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="enriched/demo/int/crm_customers",
    source=[customers_staging],
    layer=Layer.ENRICHED,
    product="demo",
    version="1.0.0",
    source_system="crm",
    is_public=True,
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
            description="Customer first name",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="first_name")],
        ),
        Attribute(
            name="last_name",
            display_name="Last Name",
            description="Customer last name",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="last_name")],
        ),
        Attribute(
            name="email",
            display_name="Email Address",
            description="Normalised email address",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="email")],
        ),
        Attribute(
            name="phone",
            display_name="Phone Number",
            description="E.164 normalised phone number",
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
            name="full_name",
            display_name="Full Name",
            description="Derived full name (first + last)",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="email_domain",
            display_name="Email Domain",
            description="Domain part of the email address (non-PII)",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="is_valid_email",
            display_name="Is Valid Email",
            description="True when email passes format validation",
            attr_type=AttrType.BOOLEAN,
        ),
        Attribute(
            name="customer_since_year",
            display_name="Customer Since Year",
            description="Year the customer record was first created",
            attr_type=AttrType.INT,
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
    ],
    retention_duration=RetentionDuration(dev=None, qua=None, prd=None),
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(customers_enriched)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=customers_enriched, enforce_schema=True),
    increment_driver_source_entity_name="customers",
)

# COMMAND ----------

# DBTITLE 1,Transform
# TODO: Implement enrichment logic.
#
# from pyspark.sql import functions as F
#
# source_df = plt_transform.read_source(customers_staging)
#
# target = source_df.select(
#     F.col("customer_id"),
#     F.col("first_name"),
#     F.col("last_name"),
#     F.col("email"),
#     F.col("phone"),
#     F.col("country_code"),
#     # Derived attributes
#     F.concat_ws(" ", F.col("first_name"), F.col("last_name")).alias("full_name"),
#     F.split(F.col("email"), "@").getItem(1).alias("email_domain"),
#     F.col("is_valid_email"),
#     F.year(F.col("created_at")).alias("customer_since_year"),
#     F.col("created_at"),
#     F.col("updated_at"),
# )

# COMMAND ----------

# DBTITLE 1,End Transform
target = None  # Replace None with the transformed DataFrame when ready
plt_transform.end_transform(target)
