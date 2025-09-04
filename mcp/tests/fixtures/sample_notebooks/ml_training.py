# ML Training Pipeline for Customer Churn Prediction

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from pyspark.sql import functions as F
import databricks.feature_store as fs

# Initialize MLflow
mlflow.set_experiment("/Users/ml_team/customer_churn_experiment")

# Parameters
dbutils.widgets.text("training_date", "2024-01-01")
dbutils.widgets.text("model_name", "customer_churn_model")
dbutils.widgets.dropdown("register_model", "false", ["true", "false"])

training_date = dbutils.widgets.get("training_date")
model_name = dbutils.widgets.get("model_name")
register_model = dbutils.widgets.get("register_model") == "true"

# Load features from feature store
fs_client = fs.FeatureStoreClient()
feature_table = "main.ml.customer_features"

# Read training data
training_df = spark.sql(f"""
    SELECT 
        customer_id,
        churn_label,
        tenure_months,
        monthly_charges,
        total_charges,
        num_products,
        support_tickets,
        satisfaction_score
    FROM main.ml.training_data
    WHERE training_date = '{training_date}'
""")

# Convert to pandas for sklearn
pdf = training_df.toPandas()

# Prepare features and labels
feature_cols = ['tenure_months', 'monthly_charges', 'total_charges', 
                'num_products', 'support_tickets', 'satisfaction_score']
X = pdf[feature_cols]
y = pdf['churn_label']

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Start MLflow run
with mlflow.start_run(run_name=f"rf_training_{training_date}") as run:
    
    # Log parameters
    mlflow.log_param("training_date", training_date)
    mlflow.log_param("n_training_samples", len(X_train))
    mlflow.log_param("n_features", len(feature_cols))
    
    # Grid search for best parameters
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [10, 20, None],
        'min_samples_split': [2, 5]
    }
    
    rf = RandomForestClassifier(random_state=42)
    grid_search = GridSearchCV(rf, param_grid, cv=5, scoring='f1')
    grid_search.fit(X_train_scaled, y_train)
    
    # Best model
    best_model = grid_search.best_estimator_
    
    # Log best parameters
    for param, value in grid_search.best_params_.items():
        mlflow.log_param(f"best_{param}", value)
    
    # Make predictions
    y_pred = best_model.predict(X_test_scaled)
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("precision", precision)
    mlflow.log_metric("recall", recall)
    mlflow.log_metric("f1_score", f1)
    
    # Log model
    mlflow.sklearn.log_model(
        best_model, 
        "random_forest_model",
        input_example=X_train_scaled[:5]
    )
    
    # Log scaler as artifact
    mlflow.sklearn.log_model(scaler, "scaler")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    # Log feature importance as artifact
    feature_importance.to_csv("/tmp/feature_importance.csv", index=False)
    mlflow.log_artifact("/tmp/feature_importance.csv")
    
    print(f"Model trained with F1 score: {f1:.4f}")
    
    # Register model if requested
    if register_model:
        model_uri = f"runs:/{run.info.run_id}/random_forest_model"
        model_version = mlflow.register_model(model_uri, model_name)
        
        # Transition to staging
        client = mlflow.tracking.MlflowClient()
        client.transition_model_version_stage(
            name=model_name,
            version=model_version.version,
            stage="Staging"
        )
        
        print(f"Model registered as {model_name} version {model_version.version}")

# Save predictions to table for analysis
predictions_df = spark.createDataFrame(
    pd.DataFrame({
        'customer_id': pdf.loc[X_test.index, 'customer_id'],
        'actual': y_test,
        'predicted': y_pred,
        'prediction_date': training_date
    })
)

predictions_df.write \
    .mode("append") \
    .saveAsTable("main.ml.churn_predictions")