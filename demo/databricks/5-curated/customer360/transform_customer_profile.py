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

# Source — enriched customers entity
customers_enriched = Entity(
    entity_name="customers",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="enriched/demo/int/crm_customers",
    source=[],
    layer=Layer.ENRICHED,
    product="demo",
    version="1.0.0",
    source_system="crm",
    is_public=True,
    parameter=[],
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[],
)

# Target — curated customer 360 profile
customer_profile_curated = Entity(
    entity_name="customer_profile",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="curated/demo/customer_profile",
    source=[customers_enriched],
    layer=Layer.CURATED,
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
            description="Unique customer identifier — the master business key",
            is_key=True,
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="full_name",
            display_name="Full Name",
            description="Customer full name (first + last)",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="full_name")],
        ),
        Attribute(
            name="email",
            display_name="Email Address",
            description="Primary contact email",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="email")],
        ),
        Attribute(
            name="phone",
            display_name="Phone Number",
            description="Primary contact phone in E.164 format",
            attr_type=AttrType.STRING,
            parameter=[Parameter(name="pii", value="phone")],
        ),
        Attribute(
            name="country_code",
            display_name="Country Code",
            description="ISO 3166-1 alpha-2 country",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="email_domain",
            display_name="Email Domain",
            description="Non-PII email domain for segmentation",
            attr_type=AttrType.STRING,
        ),
        Attribute(
            name="is_valid_contact",
            display_name="Is Valid Contact",
            description="True when both email and phone are valid",
            attr_type=AttrType.BOOLEAN,
        ),
        Attribute(
            name="customer_since_year",
            display_name="Customer Since Year",
            description="Year the customer was first created",
            attr_type=AttrType.INT,
        ),
        Attribute(
            name="customer_tenure_years",
            display_name="Customer Tenure (Years)",
            description="Number of full years since the customer was created",
            attr_type=AttrType.INT,
        ),
        Attribute(
            name="source_created_at",
            display_name="Source Created At",
            description="Original creation timestamp from the source system",
            attr_type=AttrType.TIMESTAMP,
        ),
        Attribute(
            name="source_updated_at",
            display_name="Source Updated At",
            description="Latest update timestamp from the source system",
            attr_type=AttrType.TIMESTAMP,
        ),
    ],
    retention_duration=RetentionDuration(dev=None, qua=None, prd=None),
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(customer_profile_curated)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=customer_profile_curated, enforce_schema=True),
    increment_driver_source_entity_name="customers",
)

# COMMAND ----------

# DBTITLE 1,Transform
# TODO: Implement curated merge/upsert logic.
#
# from pyspark.sql import functions as F
# from datetime import date
#
# source_customers_enriched = plt_transform.read_source(customers_enriched)
#
# current_year = date.today().year
#
# target = source_customers_enriched.select(
#     F.col("customer_id"),
#     F.col("full_name"),
#     F.col("email"),
#     F.col("phone"),
#     F.col("country_code"),
#     F.col("email_domain"),
#     (F.col("is_valid_email") & F.col("phone").isNotNull()).alias("is_valid_contact"),
#     F.col("customer_since_year"),
#     (F.lit(current_year) - F.col("customer_since_year")).alias("customer_tenure_years"),
#     F.col("created_at").alias("source_created_at"),
#     F.col("updated_at").alias("source_updated_at"),
# )

# COMMAND ----------

# DBTITLE 1,End Transform
target = None  # Replace None with the transformed DataFrame when ready
plt_transform.end_transform(target)
