# Databricks notebook source
# MAGIC %md
# MAGIC # ETL Pipeline for Sales Data
# MAGIC This notebook processes daily sales data from bronze to silver layer

# COMMAND ----------

# MAGIC %python
# Import required libraries
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum, avg, count, current_date
from delta.tables import DeltaTable
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# COMMAND ----------

# Setup parameters
dbutils.widgets.text("processing_date", "2024-01-01", "Date to process (YYYY-MM-DD)")
dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"], "Target environment")
dbutils.widgets.text("batch_size", "10000", "Batch size for processing")

# Get parameters
processing_date = dbutils.widgets.get("processing_date")
environment = dbutils.widgets.get("environment")
batch_size = int(dbutils.widgets.get("batch_size"))

logger.info(f"Processing date: {processing_date}, Environment: {environment}")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Check source data quality
# MAGIC SELECT 
# MAGIC   COUNT(*) as total_records,
# MAGIC   COUNT(DISTINCT transaction_id) as unique_transactions,
# MAGIC   SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) as null_amounts
# MAGIC FROM main.bronze.sales_transactions
# MAGIC WHERE transaction_date = '${processing_date}'

# COMMAND ----------

# Read source data from bronze layer
source_df = spark.read.table("main.bronze.sales_transactions")
customers_df = spark.read.table("main.bronze.customers")

# Filter for processing date
daily_transactions = source_df.filter(col("transaction_date") == processing_date)

logger.info(f"Processing {daily_transactions.count()} transactions for {processing_date}")

# COMMAND ----------

# Data quality checks and transformations
cleaned_df = daily_transactions \
    .filter(col("amount") > 0) \
    .filter(col("transaction_id").isNotNull()) \
    .dropDuplicates(["transaction_id"])

# Enrich with customer data
enriched_df = cleaned_df.join(
    customers_df,
    cleaned_df.customer_id == customers_df.id,
    "left"
).select(
    cleaned_df["*"],
    customers_df.customer_name,
    customers_df.customer_segment,
    customers_df.region
)

# COMMAND ----------

# Calculate aggregations
daily_summary = enriched_df.groupBy("customer_segment", "region") \
    .agg(
        count("transaction_id").alias("transaction_count"),
        sum("amount").alias("total_revenue"),
        avg("amount").alias("avg_transaction_value")
    ) \
    .withColumn("processing_date", current_date()) \
    .withColumn("environment", lit(environment))

# COMMAND ----------

# Write to silver layer
output_table = f"main.silver.daily_sales_summary"

# Use merge for idempotent writes
if DeltaTable.isDeltaTable(spark, output_table):
    delta_table = DeltaTable.forName(spark, output_table)
    
    delta_table.alias("target") \
        .merge(
            daily_summary.alias("source"),
            "target.customer_segment = source.customer_segment AND target.region = source.region AND target.processing_date = source.processing_date"
        ) \
        .whenMatchedUpdateAll() \
        .whenNotMatchedInsertAll() \
        .execute()
else:
    daily_summary.write \
        .mode("overwrite") \
        .saveAsTable(output_table)

logger.info(f"Successfully wrote {daily_summary.count()} records to {output_table}")

# COMMAND ----------

# Run data quality checks notebook
quality_check_result = dbutils.notebook.run(
    "/Shared/data_quality/validate_silver_data",
    timeout_seconds=600,
    arguments={
        "table_name": output_table,
        "date": processing_date
    }
)

if quality_check_result != "PASSED":
    raise ValueError(f"Data quality checks failed: {quality_check_result}")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Final validation
# MAGIC SELECT 
# MAGIC   customer_segment,
# MAGIC   region,
# MAGIC   SUM(total_revenue) as total,
# MAGIC   AVG(avg_transaction_value) as avg_value
# MAGIC FROM main.silver.daily_sales_summary
# MAGIC WHERE processing_date = current_date()
# MAGIC GROUP BY customer_segment, region
# MAGIC ORDER BY total DESC

# COMMAND ----------

# Return success status
dbutils.notebook.exit("SUCCESS")