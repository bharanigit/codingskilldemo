# Databricks notebook source
# Platform framework initialisation — equivalent to %run "../../_platform_app/plt_init"
#
# In a real environment this bootstraps the platform framework, sets up logging,
# and makes lake_connection / execution_context available globally.
# Here we bootstrap the mock pltdata package from the demo directory.

# COMMAND ----------

import sys, os

# Add demo/ to sys.path so `import pltdata` resolves to the mock package
_init_dir = os.path.dirname(os.path.abspath(__file__))          # _platform_app/
_databricks_dir = os.path.dirname(_init_dir)                    # databricks/
_demo_dir = os.path.dirname(_databricks_dir)                    # demo/
if _demo_dir not in sys.path:
    sys.path.insert(0, _demo_dir)

# COMMAND ----------

from pltdata import (
    Layer, AttrType, EntityType, FieldType,
    Parameter, EntityProperty, RetentionDuration,
    Attribute, Entity, Drl,
    PltDebugTransform, PltDataFrame, LifecycleHandler,
    Deploy, LakeConnectFactory, SchemaTranslate,
)

lake_connection = LakeConnectFactory().lake_connection
print(f"[platform_init] framework loaded | environment={lake_connection.product_environment!r}")

# COMMAND ----------
