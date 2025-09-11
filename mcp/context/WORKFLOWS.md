# DAB Generation Workflows

## Workflow 1: Notebook/Folder → Bundle
**User Goal**: Convert existing notebooks into a scheduled job bundle

**Steps**:
1. **Analyze**: `analyze_notebook` on notebook(s) or folder
2. **Get Cluster Config**: Ask user for cluster ID or use serverless
   - If cluster ID provided: Fetch cluster config via API
   - If serverless: Use default serverless configuration
3. **Generate Bundle**: Create DAB with job_clusters based on reference cluster
4. **Validate**: Run bundle validation
5. **Deploy**: User deploys with `databricks bundle deploy`

**Example Commands**:
```
"Analyze the notebooks in /Workspace/Users/me/etl/"
"Use cluster 1234-567890-abc123 as reference"
"Generate bundle called data-pipeline"
```

## Workflow 2: Existing Job → Bundle
**User Goal**: Convert existing Databricks job to DAB format

**Steps**:
1. **Use Built-in Tool**: `generate_bundle_from_job` leverages official CLI
2. **Automatic Conversion**: CLI handles job clusters, tasks, schedules, notifications
3. **Validate**: Run bundle validation on generated configuration
4. **Deploy**: User can deploy alongside or replace original job

**Example Commands**:
```
"Generate bundle from job ID 123456"
"Convert job 'Daily ETL Pipeline' to bundle format"
```

**CLI Command Used**: `databricks bundle generate job --existing-job-id <job_id>`

## Workflow 3: Existing Pipeline → Bundle
**User Goal**: Convert DLT pipeline to bundle format

**Steps**:
1. **Export Pipeline**: Fetch pipeline configuration
2. **Extract Notebooks**: Identify pipeline notebooks and dependencies
3. **Generate Bundle**: Create bundle with pipeline resource
4. **Add Serverless**: Use `serverless: true` for DLT pipelines
5. **Validate & Deploy**

**Example Commands**:
```
"Convert my DLT pipeline 'bronze-silver-gold' to bundle"
```

## Workflow 4: Mixed Resources → Bundle
**User Goal**: Bundle multiple jobs, pipelines, and notebooks together

**Steps**:
1. **Inventory Resources**: List jobs, pipelines, notebooks to include
2. **Analyze Dependencies**: Check for shared clusters, schedules
3. **Consolidate Config**: Create unified bundle with multiple resources
4. **Optimize**: Share job clusters where appropriate
5. **Generate & Validate**

## Decision Tree: Cluster Configuration

```
Notebook task?
├─ Yes → Prefer serverless (no cluster config needed)
└─ No (Python/Wheel/SQL) → Need cluster

Need cluster?
├─ User has preferred cluster ID → Fetch config, create job_cluster
├─ User wants serverless → Use environment_key + environments
└─ No preference → Ask for cluster ID or suggest serverless
```

## Common User Inputs
- **Cluster ID**: "1234-567890-abc123"
- **Notebook paths**: "/Workspace/Users/me/notebooks/"
- **Job ID**: "987654321"
- **Pipeline name**: "my-dlt-pipeline"
- **Bundle name**: "data-processing-pipeline"
- **Target environment**: "dev" | "staging" | "prod"