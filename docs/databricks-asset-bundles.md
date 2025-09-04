Databricks Asset Bundles: Comprehensive Guide
=============================================

Databricks Asset Bundles (“bundles” or “DABs”) enable you to define, version, and deploy Databricks resources—such as jobs, pipelines, notebooks, and more—as code. Asset Bundles bring CI/CD, reproducibility, and structured collaboration to the Databricks experience by co-versioning not just code but also data asset configurations, making it straightforward to maintain and deploy end-to-end data solutions.

---

Table of Contents
-----------------
- Overview
- Key Concepts
- Directory and File Structure Example
- YAML Configuration Examples
    - Bundle Metadata (databricks.yml)
    - Job Definition
    - Pipeline Definition
    - Experiment Resource Example
    - Cluster Resource Example
    - Dashboard Resource Example
- Working with Asset Bundles: CLI Basics
- Best Practices and Templates
- Useful Documentation Links

---

Overview
--------

Databricks Asset Bundles are collections of code artifacts and resource definitions (using YAML), checked into source control (such as Git), that specify one or more deployable Databricks assets (e.g., notebooks, jobs, pipelines, dashboards). With Asset Bundles, you can:
- Author, version, and test resources as code
- Deploy and manage all assets through repeatable CI/CD processes
- Use templates and conventions to accelerate development
- Co-version multiple sources (code, configs, tests) in a single bundle

---

Key Concepts
------------

- **Bundle:** A folder with a special databricks.yml file at its root, describing one or more deployable Databricks resources.
- **Asset:** A resource instantiated from a bundle—jobs, DLT/Lakeflow pipelines, MLflow experiments, clusters, dashboards, etc.
- **Artifact:** File-based resources (Python files, notebooks, SQL queries) referenced as part of a bundle.
- **Namespace:** A logical deployment context (e.g., dev, staging, production) allowing for multiple isolated copies per workspace or user.
- **Co-Versioning:** Multiple sources and assets, including code and configs, managed together within a bundle and versioned in source control.
- **YAML Resource Mapping:** Resources defined as YAML files, mirroring REST API payloads, extended with conveniences like variables and environment overrides.

---

Directory and File Structure Example
------------------------------------

Here’s how a typical repository might look with Databricks Asset Bundles:

```
my-data-bundle/
├── databricks.yml           # Bundle metadata & targets
├── src/
│   ├── analysis_notebook.ipynb
│   └── main.py
├── resources/
│   ├── my_job.yml           # Job definition
│   ├── my_pipeline.yml      # Pipeline definition
│   └── dashboard.json       # (Optional) Dashboard export file
├── tests/
│   └── test_logic.py
└── README.md
```
A mono-repo can contain multiple bundles, each with a separate databricks.yml and related resource/config files.

---

YAML Configuration Examples
---------------------------

### 1. Bundle Metadata (databricks.yml)

The databricks.yml file anchors a bundle, specifying its metadata and what resources are included.

```yaml
bundle:
  name: org.mycompany.sample_etl
  include:
    - ./resources/my_job.yml
    - ./resources/my_pipeline.yml
    - ./resources/dashboard.json

targets:
  development:
    workspace:
      default: true
      profile: dev-profile
  production:
    workspace:
      profile: prod-profile
```
- `include` lists all YAML and JSON files forming part of this bundle.
- `targets` defines environment profiles for deployment (dev, prod, etc.).

---

### 2. Job Resource Example

Jobs let you orchestrate notebooks, scripts, and other tasks via bundles.

```yaml
resources:
  jobs:
    my_etl_job:
      name: sample-etl-{{.unique_id}}
      description: A sample ETL job managed by a Databricks Asset Bundle
      tasks:
        - task_key: run_notebook
          notebook_task:
            notebook_path: ../src/analysis_notebook.ipynb
          cluster_key: my_cluster
      clusters:
        - cluster_key: my_cluster
          spark_version: 15.4.x-scala2.12
          node_type_id: i3.xlarge
          num_workers: 2
```
- All resource types follow the REST API "create" schema, adapted to YAML.
- Use variables such as `{{.unique_id}}` for dynamic naming (especially across branches or deployments).

---

### 3. Lakeflow Pipeline (DLT) Resource Example

Define or manage Lakeflow Declarative Pipelines (previously DLT) using YAML:

```yaml
resources:
  pipelines:
    my_pipeline:
      name: etl-pipeline-{{.unique_id}}
      libraries:
        - notebook:
            path: ../src/analysis_notebook.ipynb
      catalog: my_catalog
      target: default_schema
```
- Bundles also let you wire up the given pipeline to use code and datasets referenced locally.

---

### 4. MLflow Experiment Resource Example

```yaml
resources:
  experiments:
    experiment:
      name: my_ml_experiment
      permissions:
        - level: CAN_READ
          group_name: users
      description: MLflow experiment used to track job or pipeline runs
```
- Experiments, permissions, and metadata can all be bundled.

---

### 5. Cluster Resource Example

```yaml
resources:
  clusters:
    my_cluster:
      spark_version: 15.4.x-scala2.12
      node_type_id: i3.xlarge
      num_workers: 2
      enable_elastic_disk: true
      policy_id: abcdefg-1234567 # (Optional)
```
- More advanced settings (e.g. auto-scaling) can be set as supported by the Databricks REST API.

---

### 6. Dashboard Resource Example

```yaml
resources:
  dashboards:
    taxi_trip_analysis:
      file_path: ../resources/dashboard.json
```
- Dashboards are exported as `.json` and referenced by file path in the bundle.
- When using Git-backed dashboards, add rules to avoid accidental duplicate deployments.

---

Working with Asset Bundles: CLI Basics
--------------------------------------

Bundles are managed using the Databricks CLI (v0.205+). Key commands include:

- **Initialize a bundle from a template:**
  ```bash
  databricks bundle init --template https://github.com/databricks/bundle-examples
  ```
- **Generate resource YAML from an existing workspace object:**
  ```bash
  databricks bundle generate
  ```
- **Deploy the bundle to the current target:**
  ```bash
  databricks bundle deploy --target development
  ```
- **Validate the bundle config:**
  ```bash
  databricks bundle validate
  ```
- **Run tests (where supported):**
  ```bash
  databricks bundle test
  ```

See the CLI reference for full details.

---

Best Practices and Templates
----------------------------

- **Start from a template:** Use the official templates or community bundles as a starting point, and customize as needed.
- **Explicitly include all assets/artifacts**: This ensures reproducibility.
- **Namespace assets** for per-user or per-environment development to avoid name clashes.
- **Co-version tests** alongside logic for robust CI/CD.
- **Use variable interpolation** for dynamic naming across environments.
- **Leverage scripts section** in YAML for build/test hooks when working with compiled artifacts (Python, Java, Scala).
- See example repositories such as `github.com/databricks/dab-samples`.

---

Useful Documentation Links
-------------------------

- [Databricks Asset Bundles Examples Repository] (GitHub: databricks/bundle-examples and databricks/dab-samples)
- [Resource Mapping and Supported YAML Schema (AWS)] (https://docs.databricks.com/aws/en/dev-tools/bundles/resourcesicks Documentation)
- [Databricks CLI Reference: bundle commands] (Databricks official docs)
- [Develop a job with Databricks Asset Bundles] (https://docs.databricks.com/aws/en/dev-tools/bundles/jobs-tutorial)
- [Develop Lakeflow Declarative Pipelines with Bundles] (https://docs.databricks.com/aws/en/dev-tools/bundles/pipelines-tutorial)

Note: For the latest updates, API changes, and sample configurations for Azure and GCP, refer to their respective documentation sections.

---

References
----------

The information and code samples above draw from internal documentation, official public docs, and Databricks engineering best practices.

---

If you have further questions or need help with specific use cases (such as MLOps, dbt integration, or complex CI/CD flows), check out the examples repositories or explore the referenced docs above.