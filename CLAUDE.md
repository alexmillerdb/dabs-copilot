Databricks Bundles Co‑pilot — CLAUDE.md

## Purpose

- Generate, validate, and (optionally) deploy Databricks Asset Bundles (DAB) to a dev target.
- Support two entry paths: derive from existing Jobs/Pipelines or infer from workspace code.

## Assumptions

- Databricks CLI is authenticated (profile) or environment variables are set; otherwise MCP Databricks tools provide access.
- Default target is dev unless specified.
- Output goes to a new bundle directory; do not modify unrelated files.

## Core Use Cases

### 1) Job → Bundle
- Input: Databricks Job ID or name.
- Steps: Fetch job config → analyze referenced notebooks/files → generate bundle → validate.
- Output: `databricks.yml` with appropriate clusters, tasks, variables.

### 2) Workspace Path → Bundle
- Input: Workspace path(s), e.g., `/Workspace/Users/...` or `/Workspace/Repos/...`.
- Steps: List/export notebooks → analyze code patterns and dependencies → generate bundle → upload/validate.
- Output: Multi-resource bundle based on detected workload (jobs, pipelines).

## Inputs To Request When Missing

- Workspace host/profile (dev target).
- Source: Job/Pipeline ID or workspace path(s).
- Bundle name and destination directory.
- Cluster/runtime preferences and any variable/secret placeholders.

## Available Tools (via MCP)

- Jobs/workspace basics: `list_jobs`, `get_job`, `run_job`, `list_notebooks`, `export_notebook`, `execute_dbsql`, `list_warehouses`, `list_dbfs_files`, `get_cluster`, `health`.
- DAB generation/validation: `analyze_notebook`, `generate_bundle`, `generate_bundle_from_job`, `validate_bundle`.
- Workspace bundle ops: `upload_bundle`, `run_bundle_command`, `sync_workspace_to_local`.
- Filesystem write when needed to create `databricks.yml`.

## Workflow Overview

1. Plan: confirm source (Job/Pipeline vs. workspace path) and gather missing inputs.
2. Discover:
   - Job flow: call `get_job(job_id)` and collect notebook/python entrypoints from tasks.
   - Workspace flow: call `list_notebooks(path, recursive)` and `export_notebook` as needed.
3. Analyze: for each entrypoint, call `analyze_notebook(notebook_path)` to infer workflow type, libraries, parameters.
4. Synthesize: call `generate_bundle(bundle_name, file_paths, output_path)` (or `generate_bundle_from_job(job_id, output_dir)` when appropriate). Write the resulting `databricks.yml`.
5. Validate: call `validate_bundle(bundle_path, target=dev)`. If errors, fix and re-validate.
6. Deliver: optionally `upload_bundle(yaml_content, bundle_name)` and provide next steps; otherwise return local path and README.

Error Recovery (apply as needed)
- Authentication issues: prompt for profile/host or token; rerun `health`.
- Missing resources: suggest alternatives or ask for corrected IDs/paths.
- Validation failures: surface exact errors, propose minimal edits, re-validate.

## Generation Guidance

### From Existing Job
- Use complete job settings (tasks, clusters, schedules, permissions) from `get_job`.
- Keep required IDs; prefer readable names elsewhere.
- For `new_cluster`: either inline under `job_clusters` or promote to `resources.clusters` and reference by key.
- Extract libraries, task params, and environment (spark_version, node_type, policy, init scripts).
- Parameterize environment-specific values; reference secrets rather than inlining.

### From Workspace Code
- Detect entrypoints: notebooks, DLT usage, SQL/Python tasks, wheels.
- Infer jobs/tasks from entrypoints; keep clusters minimal (prefer serverless/small where sensible).
- Add `artifacts` only when necessary (e.g., building wheels); otherwise reference workspace paths.

## Minimal Bundle Skeleton

```yaml
bundle:
  name: {{BUNDLE_NAME}}

variables:
  project_root:
    description: Base workspace path for code
    default: /Workspace/Repos/your-org/your-repo
  default_storage_location:
    description: External storage for outputs
    default: dbfs:/tmp/{{BUNDLE_NAME}}

targets:
  dev:
    default: true
    workspace:
      host: {{WORKSPACE_HOST}}
      root_path: /Workspace/Users/{{USER}}/bundles/{{BUNDLE_NAME}}-dev
    run_as:
      user_name: {{USER_EMAIL}}

resources:
  jobs:
    {{JOB_KEY}}:
      name: {{BUNDLE_NAME}} - dev job
      job_clusters:
        - job_cluster_key: shared-small
          new_cluster:
            spark_version: 13.3.x-scala2.12
            num_workers: 1
      tasks:
        - task_key: main
          job_cluster_key: shared-small
          notebook_task:
            notebook_path: ${var.project_root}/jobs/main
          libraries: []
```

## Validation, Deployment, Upload

- Validate: `databricks bundle validate`
- Deploy (dev): `databricks bundle deploy -t dev`
- Optional upload: use `upload_bundle(yaml_content, bundle_name)` and show workspace path + next steps.

## Response Guidelines

- Progress: concise, step-by-step updates (e.g., “Analyzing 2/3 notebooks…”).
- Results: show structured outputs for tool calls (tables for jobs, JSON for configs).
- Errors: be explicit, propose the exact fix, then retry.

## Quality & Security Standards

- Minimal first: include only necessary resources.
- Parameterize environment- or path-like values under `variables`.
- No secrets in plain text; use scopes/secret references.
- Consistent naming (kebab-case keys, readable resource names).
- Include a short README with validate/deploy/run instructions.

## README Snippet

```markdown
# {{BUNDLE_NAME}} (dev)

Commands:
- Validate: `databricks bundle validate`
- Deploy: `databricks bundle deploy -t dev`

Edit bundle settings in `databricks.yml`. Update variables under `variables:` or set via environment/CLI.
```

## When To Ask

- Missing host/profile or ambiguous source selection.
- Conflicting/incomplete job/pipeline definitions.
- Required cluster/runtime not provided.
- MCP/CLI permission or API errors.