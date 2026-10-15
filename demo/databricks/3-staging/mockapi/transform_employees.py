# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %md
# MAGIC Staging job created via wizard
# MAGIC ### Data information
# MAGIC * Layer:               STAGING
# MAGIC * Entity:              employees
# MAGIC ### Notebook information
# MAGIC
# MAGIC Uses Platform Development Framework

# COMMAND ----------

# MAGIC %run "../../_platform_app/plt_init"

# COMMAND ----------

# DBTITLE 1,Entity Definition
mockapi_employees_staging = Entity(
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
        Attribute(
            name="employee_id",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/employee_id"],
        ),
        Attribute(
            name="first_name",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/first_name"],
            parameter=[Parameter(name="pii", value="first_name")],
        ),
        Attribute(
            name="last_name",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/last_name"],
            parameter=[Parameter(name="pii", value="last_name")],
        ),
        Attribute(
            name="email",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/email"],
            parameter=[Parameter(name="pii", value="email")],
        ),
        Attribute(
            name="phone",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/phone"],
            parameter=[Parameter(name="pii", value="phone")],
        ),
        Attribute(
            name="department",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/department"],
        ),
        Attribute(
            name="job_title",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/job_title"],
        ),
        Attribute(
            name="salary",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/salary"],
            parameter=[Parameter(name="pii", value="salary")],
        ),
        Attribute(
            name="hire_date",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/hire_date"],
        ),
        Attribute(
            name="manager_id",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/manager_id"],
        ),
        Attribute(
            name="office_location",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/office_location"],
        ),
        Attribute(
            name="status",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/status"],
        ),
        Attribute(
            name="created_at",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/created_at"],
        ),
        Attribute(
            name="updated_at",
            attr_type=AttrType.STRING,
            source=["raw/cq/mockapi/int/employees/updated_at"],
        ),
        Attribute(name="UploadDate", attr_type=AttrType.TIMESTAMP),
    ],
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(mockapi_employees_staging)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    target=Drl.from_object(entity=mockapi_employees_staging, enforce_schema=True),
    target_persist=True,
    target_merge_type=TargetMergeType.FULL_REPLACE,
    lifecycle_handler=StagingIngestionLifecycleHandler(
        "raw/cq/mockapi/int/employees",
        mockapi_employees_staging.entity_locator
    ),
    increment_driver_source_entity_name="employees",
    source_employees_raw=Drl.from_config(
        entity_name="employees",
        product="cq",
        module="int",
        layer=Layer.RAW,
        source_system="mockapi"
    )
)

# COMMAND ----------

# DBTITLE 1,Logger and Lifecycle Handler
logger = PltLogger("employees")

try:
    # Running in compiled transformations
    staging_lifecycle_handler = lifecycle_handler
except NameError:
    # Development mode in notebook
    staging_lifecycle_handler = plt_transform._lifecycle_handler

all_uploads = staging_lifecycle_handler.files_to_process
logger.info("All folders to process: %s", "\n".join([str(f) for f in all_uploads]))

# COMMAND ----------

# DBTITLE 1,Data transformation
target = None
for uploaded_file in all_uploads:
    employees_staging_source = Entity(
        entity_name="employees",
        entity_type=EntityType.DELTA,
        module_name="int",
        entity_locator="raw/cq/mockapi/int/employees",
        layer=Layer.RAW,
        product="cq",
        version="1.0.0",
        source_system="mockapi",
        is_public=False,
        entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
        attributes=[],
    )

    if read_dataframe(uploaded_file) is None:
        continue

    source_hdf = PltDataFrame(
        read_dataframe(uploaded_file),
        Drl.from_object(employees_staging_source, enforce_schema=False),
    )

    transform_hdf = source_hdf
    transform_hdf = transform_hdf.withColumn(
        "UploadDate",
        to_timestamp(lit(uploaded_file.UploadDate), "yyyy-MM-dd HH:mm:ss.SSSSSSS"),
    )
    for attr in mockapi_employees_staging.attributes:
        source_locator = (
            attr.name
            if attr.source is None or len(attr.source) == 0
            else attr.source[0]
        )
        source_split = source_locator.split("/")
        source_name = source_split[len(source_split) - 1]
        if source_name == attr.name and source_name in transform_hdf.columns:
            continue
        else:
            if source_name in transform_hdf.columns:
                transform_hdf = transform_hdf.withColumnRenamed(source_name, attr.name)
            elif source_name not in transform_hdf.columns:
                field = SchemaTranslate.get_spark_type(attr)
                transform_hdf = transform_hdf.withColumn(
                    attr.name, f.lit(None).cast(field.dataType)
                )

    for col in transform_hdf.columns:
        if len([a for a in mockapi_employees_staging.attributes if a.name == col]) == 0:
            transform_hdf = transform_hdf.drop(col)

    if target:
        target = target.unionByName(transform_hdf, allowMissingColumns=True)
    else:
        target = transform_hdf

# COMMAND ----------

# DBTITLE 1,End Transform
plt_transform.end_transform(target)
