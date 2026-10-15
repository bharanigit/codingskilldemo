# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %run "../../_platform_app/platform_init"

# COMMAND ----------

# DBTITLE 1,Entity Definition
ace_test_raw_genie_raw = Entity(
    entity_name="test_raw_genie",
    entity_type=EntityType.DELTA,
    module_name="int",
    entity_locator="raw/cq/ace/int/test_raw_genie",
    layer=Layer.RAW,
    product="cq",
    version="1.0.0",
    source_system="ace",
    is_public=False,
    entity_property=EntityProperty(auto_compute_hash=True, auto_compute_loadinfo=True),
    attributes=[
        Attribute(name="id", attr_type=AttrType.STRING),
        Attribute(name="name", attr_type=AttrType.STRING),
    ],
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(ace_test_raw_genie_raw)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=ace_test_raw_genie_raw, enforce_schema=False),
    target_persist=False,
    target_merge_type=TargetMergeType.FULL_REPLACE,
    increment_driver_source_entity_name=None
)

# COMMAND ----------

# DBTITLE 1,Fetches Ingest date details
import json
from pltdata import IngestInfoContext
from datetime import datetime, timedelta

max_days = 5
ingest_info_context = IngestInfoContext()
ingested_data = ingest_info_context.read_all(
    entity_locator=ace_test_raw_genie_raw.entity_locator, upload_days=max_days
)

# For backfilling or if no data yet ingested
if len(ingested_data) == 0:
    report_start_date = str((datetime.now() - timedelta(days=max_days)).date())
    logger.info(f"Extract first time from {report_start_date}")
else:  # For daily load
    report_start_date = str((datetime.now() - timedelta(days=1)).date())
    logger.info(f"Extract after ingest {ingested_data[0].id} from {report_start_date}")

# COMMAND ----------

# DBTITLE 1,Connecting to Delta Lake & creating Folders
lake_connection = LakeConnectFactory().lake_connection
entity_name = "test_raw_genie"
module_name = "int"

target_path = "/".join([
    lake_connection.get_root(Layer.RAW),
    f"bu={lake_connection.business_unit}",
    f"pp={lake_connection.platform_product}",
    f"sys=ace",
    f"mod={module_name}",
    f"entity={entity_name}",
])

dbutils.fs.mkdirs(target_path)

target_path_data = f"{target_path}/ingestion-date={datetime.now().strftime('%Y-%m-%d-%H:%M')}"
dbutils.fs.mkdirs(target_path_data)
print(target_path_data)

# COMMAND ----------

# DBTITLE 1,Fetch and Write Data
# TODO: Import the appropriate API client for 'ace' source system
# from integration.functions.<ace_module> import <AceApiClass>

# TODO: Initialize API client
# api_client = <AceApiClass>()

entity_fields = [att.name for att in ace_test_raw_genie_raw.attributes]

# TODO: Implement API call to fetch data
# for item in api_client.<accounts_list>:
#     try:
#         entity_val = api_client.<get_method>(entity_fields, item)
#         if entity_val is not None and len(entity_val) > 0:
#             data_json = json.dumps(entity_val, ensure_ascii=False, indent=4)
#             dbutils.fs.put(
#                 f"{target_path_data}/{item}/{report_start_date}.json",
#                 data_json,
#                 overwrite=True,
#             )
#         else:
#             print(f"No data for {item}")
#     except Exception as e:
#         raise e

size = 0  # TODO: Set to actual count of records/files written

# COMMAND ----------

# DBTITLE 1,Write Schema and Log Ingestion
dbutils.fs.put(
    f"{target_path}/schema.json",
    json.dumps(ace_test_raw_genie_raw.to_dict()),
    overwrite=True
)

ingest_info_context.create_new(
    upload_type="nested_json",
    system="ace",
    entity_name="test_raw_genie",
    folder_path=target_path_data,
    folder_size=size
)

# COMMAND ----------

# DBTITLE 1,End Transform
plt_transform.end_transform(None)
