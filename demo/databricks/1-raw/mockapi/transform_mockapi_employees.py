# Databricks notebook source
# /// script
# [tool.databricks.environment]
# base_environment = "/Workspace/Shared/environment/int-default-env.yml"
# ///
# MAGIC %run "../../_platform_app/plt_init"

# COMMAND ----------

# DBTITLE 1,Entity Definition
mockapi_employees_raw = Entity(
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
    retention_duration=RetentionDuration(dev=30, qua=90, prd=None),
    attributes=[
        Attribute(name="employee_id", attr_type=AttrType.STRING),
        Attribute(name="first_name", attr_type=AttrType.STRING),
        Attribute(name="last_name", attr_type=AttrType.STRING),
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
        Attribute(
            name="salary",
            attr_type=AttrType.DOUBLE,
            parameter=[Parameter(name="pii", value="salary")],
        ),
        Attribute(name="hire_date", attr_type=AttrType.DATE),
        Attribute(name="manager_id", attr_type=AttrType.STRING),
        Attribute(name="office_location", attr_type=AttrType.STRING),
        Attribute(name="status", attr_type=AttrType.STRING),
        Attribute(name="created_at", attr_type=AttrType.TIMESTAMP),
        Attribute(name="updated_at", attr_type=AttrType.TIMESTAMP),
    ],
)

# COMMAND ----------

# DBTITLE 1,Deploy Entity
Deploy().deploy_entity(mockapi_employees_raw)

# COMMAND ----------

# DBTITLE 1,Platform Debug Transform
plt_transform = PltDebugTransform(
    notebook_variables=vars(),
    version="1.0.0",
    target=Drl.from_object(entity=mockapi_employees_raw, enforce_schema=False),
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
    entity_locator=mockapi_employees_raw.entity_locator, upload_days=max_days
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
entity_name = "employees"
module_name = "int"

target_path = "/".join([
    lake_connection.get_root(Layer.RAW),
    f"bu={lake_connection.business_unit}",
    f"pp={lake_connection.platform_product}",
    f"sys=mockapi",
    f"mod={module_name}",
    f"entity={entity_name}",
])

dbutils.fs.mkdirs(target_path)

target_path_data = f"{target_path}/ingestion-date={datetime.now().strftime('%Y-%m-%d-%H:%M')}"
dbutils.fs.mkdirs(target_path_data)
print(target_path_data)

# COMMAND ----------

# DBTITLE 1,Generate Synthetic Employees
import random
import uuid
from datetime import datetime, date

def generate_synthetic_employees(n=50):
    """Generate synthetic employee records matching the entity attributes."""
    dept_titles = {
        "Engineering": ["Software Engineer", "Senior Engineer", "Tech Lead"],
        "Marketing": ["Marketing Manager", "Content Strategist", "Brand Lead"],
        "Sales": ["Account Executive", "Sales Manager", "BDR"],
        "Finance": ["Financial Analyst", "Controller", "CFO"],
        "HR": ["HR Manager", "Recruiter", "People Partner"],
        "Operations": ["Operations Manager", "Analyst", "Coordinator"],
    }
    first_names = [
        "Alice", "Bob", "Carlos", "Diana", "Ethan", "Fatima", "George",
        "Hannah", "Ivan", "Julia", "Kevin", "Laura", "Marco", "Nina",
        "Oscar", "Priya", "Quinn", "Rachel", "Sam", "Tina",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Martinez", "Wilson", "Anderson", "Taylor", "Thomas",
        "Jackson", "White", "Harris", "Martin", "Thompson", "Young", "Lee",
    ]

    records = []
    for _ in range(n):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        department = random.choice(list(dept_titles.keys()))
        hire_dt = date(
            random.randint(2015, 2024),
            random.randint(1, 12),
            random.randint(1, 28),
        )
        record = {
            "employee_id": str(uuid.uuid4()),
            "first_name": first_name,
            "last_name": last_name,
            "email": f"{first_name.lower()}.{last_name.lower()}@mockapi.io",
            "phone": f"+1-555-{random.randint(1000000, 9999999)}",
            "department": department,
            "job_title": random.choice(dept_titles[department]),
            "salary": round(random.uniform(45000, 150000), 2),
            "hire_date": hire_dt.isoformat(),
            "manager_id": str(uuid.uuid4()) if random.random() > 0.1 else None,
            "office_location": random.choice(["London", "Paris", "Toronto", "Sydney", "Singapore"]),
            "status": "active" if random.random() < 0.85 else "inactive",
            "created_at": f"{hire_dt.isoformat()}T00:00:00",
            "updated_at": datetime.utcnow().isoformat(),
        }
        records.append(record)
    return records

employees_data = generate_synthetic_employees(50)

if employees_data is not None and len(employees_data) > 0:
    data_json = json.dumps(employees_data, ensure_ascii=False, indent=4)
    dbutils.fs.put(
        f"{target_path_data}/employees/{report_start_date}.json",
        data_json,
        overwrite=True,
    )
    size = len(employees_data)
else:
    print("No data generated")
    size = 0

# COMMAND ----------

# DBTITLE 1,Build Spark DataFrame
from pyspark.sql.types import DateType, TimestampType, DoubleType

employees_df = spark.createDataFrame(employees_data)
employees_df = (
    employees_df
    .withColumn("hire_date", employees_df["hire_date"].cast(DateType()))
    .withColumn("created_at", employees_df["created_at"].cast(TimestampType()))
    .withColumn("updated_at", employees_df["updated_at"].cast(TimestampType()))
    .withColumn("salary", employees_df["salary"].cast(DoubleType()))
)

# COMMAND ----------

# DBTITLE 1,Write Schema and Log Ingestion
dbutils.fs.put(
    f"{target_path}/schema.json",
    json.dumps(mockapi_employees_raw.to_dict()),
    overwrite=True
)

ingest_info_context.create_new(
    upload_type="nested_json",
    system="mockapi",
    entity_name="employees",
    folder_path=target_path_data,
    folder_size=size
)

# COMMAND ----------

# DBTITLE 1,End Transform
plt_transform.end_transform(None)
