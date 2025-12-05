# Databricks Apps Patterns

Complete patterns for building and deploying Databricks Apps using Asset Bundles.

---

## Overview

Databricks Apps are custom web applications deployed on Databricks infrastructure. They can:
- Display dashboards and visualizations
- Manage and trigger jobs
- Provide data exploration interfaces
- Integrate with model serving endpoints

---

## App Project Structure

```
my-app/
├── databricks.yml
├── resources/
│   └── apps.yml
├── src/
│   └── app/
│       ├── app.py           # Flask/Gradio/Streamlit app
│       ├── app.yml          # Runtime configuration
│       └── templates/       # HTML templates (Flask)
└── README.md
```

---

## databricks.yml

```yaml
bundle:
  name: my-app

include:
  - resources/*.yml

variables:
  app_name:
    description: Application name
    default: my-app

targets:
  dev:
    mode: development
    default: true

  prod:
    mode: production
    run_as:
      service_principal_name: sp-apps-prod
```

---

## resources/apps.yml

```yaml
resources:
  apps:
    job_manager:
      name: '${var.app_name}-${bundle.target}'
      description: 'An app which manages a Databricks job'
      source_code_path: ./src/app

      # Resource bindings - connect to other DAB resources
      resources:
        - name: 'app-job'
          job:
            id: ${resources.jobs.my_job.id}
            permission: 'CAN_MANAGE_RUN'

      # Optional: permissions
      permissions:
        - level: CAN_MANAGE
          group_name: app-developers
        - level: CAN_USE
          group_name: app-users
```

---

## App Resource Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | App name (lowercase alphanumeric and hyphens only) |
| `description` | string | App description |
| `source_code_path` | string | Path to app source code (e.g., `./src/app`) |
| `resources` | list | Resource bindings for jobs, secrets, SQL warehouses |
| `permissions` | list | Access control settings |
| `compute_size` | string | Compute allocation: `MEDIUM` or `LARGE` |

---

## Resource Bindings

Apps can bind to other Databricks resources:

```yaml
resources:
  apps:
    my_app:
      name: 'my-app'
      source_code_path: ./src/app
      resources:
        # Bind to a job
        - name: 'my-job'
          job:
            id: ${resources.jobs.etl_job.id}
            permission: 'CAN_MANAGE_RUN'

        # Bind to a secret
        - name: 'api-key'
          secret:
            scope: 'my-scope'
            key: 'api-key'
            permission: 'READ'

        # Bind to a SQL warehouse
        - name: 'warehouse'
          sql_warehouse:
            id: ${var.warehouse_id}
            permission: 'CAN_USE'

        # Bind to a serving endpoint
        - name: 'model-endpoint'
          serving_endpoint:
            name: ${resources.model_serving_endpoints.my_endpoint.name}
            permission: 'CAN_QUERY'
```

---

## App Source Code

### src/app/app.py (Flask Example)

```python
from flask import Flask, render_template, redirect
from databricks.sdk import WorkspaceClient
import os

app = Flask(__name__)

@app.route('/')
def index():
    # Get job ID from environment variable (set via app.yml)
    job_id = os.environ.get('JOB_ID')

    # Use Databricks SDK
    w = WorkspaceClient()
    job = w.jobs.get(job_id)
    runs = w.jobs.list_runs(job_id=job_id)

    return render_template('index.html', job=job, runs=runs)

@app.route('/run')
def trigger_run():
    job_id = os.environ.get('JOB_ID')
    w = WorkspaceClient()
    w.jobs.run_now(job_id)
    return redirect('/')
```

### src/app/app.yml (Runtime Configuration)

```yaml
command:
  - flask
  - --app
  - app
  - run
  - --debug

env:
  - name: JOB_ID
    value: "app-job"  # References resource binding name
```

---

## Streamlit App Example

### src/app/app.py

```python
import streamlit as st
from databricks.sdk import WorkspaceClient

st.title("My Dashboard")

w = WorkspaceClient()
# Use SDK to fetch and display data
```

### src/app/app.yml

```yaml
command:
  - streamlit
  - run
  - app.py
  - --server.port
  - "8000"
```

---

## Gradio App Example

### src/app/app.py

```python
import gradio as gr
from databricks.sdk import WorkspaceClient

def predict(text):
    w = WorkspaceClient()
    # Call model serving endpoint
    return result

demo = gr.Interface(fn=predict, inputs="text", outputs="text")
demo.launch(server_port=8000)
```

### src/app/app.yml

```yaml
command:
  - python
  - app.py
```

---

## Deployment Workflow

```bash
# 1. Deploy the app
databricks bundle deploy

# 2. Start the app
databricks bundle run job_manager

# 3. Open in browser
databricks bundle open

# Get app URL
databricks bundle summary
```

---

## Local Development

For Databricks CLI v0.250.0+:

```bash
# Run app locally with Databricks environment
databricks apps run-local --prepare-environment --debug
```

---

## App with Associated Job

Create an app that manages a job defined in the same bundle:

```yaml
resources:
  jobs:
    etl_job:
      name: ${bundle.name}-etl-${bundle.target}
      tasks:
        - task_key: main
          notebook_task:
            notebook_path: ./src/notebooks/etl.py

  apps:
    job_dashboard:
      name: '${bundle.name}-dashboard'
      description: 'Dashboard for monitoring ETL job'
      source_code_path: ./src/app
      resources:
        - name: 'etl-job'
          job:
            id: ${resources.jobs.etl_job.id}
            permission: 'CAN_MANAGE_RUN'
```

---

## Apps Best Practices

1. **Resource Bindings**: Use resource bindings instead of hardcoding IDs
2. **Environment Variables**: Configure runtime settings in `app.yml`
3. **Secrets**: Use secret bindings for API keys and credentials
4. **Permissions**: Set `CAN_USE` for end users, `CAN_MANAGE` for developers
5. **Local Testing**: Use `databricks apps run-local` before deploying
6. **Framework Choice**:
   - Flask: Full control, templates, REST APIs
   - Streamlit: Quick dashboards, data apps
   - Gradio: ML model interfaces
7. **Compute Size**: Use `MEDIUM` for most apps, `LARGE` for intensive workloads
