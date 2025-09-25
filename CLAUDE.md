# I am working on creating a Databricks Asset Bundles Co-pilot application that uses Claude Code and MCP to generate bundles to validate and deploy in dev. The goal is to allow users to generate bundles from existing jobs or pipelines. And also generate bundles by analyzing code located in Databricks workspace. Please create a simple but effective CLAUDE.md file to help claude code generate bundles.

Here is a concise CLAUDE.md you can add to your repo to guide Claude Code (via MCP) to generate Databricks Asset Bundles from existing jobs/pipelines or by analyzing workspace code.

Databricks Bundles Co-pilot — CLAUDE.md

### Purpose

- Help Claude Code generate, validate, and deploy Databricks Asset Bundles (DAB) to a dev target.
- Support two entry paths: derive a bundle from existing Jobs/Pipelines, or infer a bundle by analyzing code in the Databricks workspace.


### Assumptions

- Databricks CLI is authenticated locally, or MCP Databricks tools provide equivalent access.
- Default target is dev only. Additional targets are out of scope unless explicitly requested.
- Git workspace is clean; output will be generated in a new bundle directory.


### Available tools

- MCP Databricks: list/get Jobs, Pipelines, Workspace files.
- Filesystem: read/write project files.
- Shell: run databricks bundle validate and deploy.
- Git: create branches/commits (optional).


### Inputs Claude can ask for

- Databricks workspace host and profile to target for dev.
- Source selection:
    - Existing Job name/ID or Pipeline name/ID
    - Workspace path(s) to analyze (e.g., /Workspace/Repos/... or /Workspace/Users/...)
- Bundle name and destination folder (e.g., bundles/my-app).
- Default cluster policy or runtime, and any secret/variable placeholders.


### Workflow overview

- Plan: Confirm path (existing Job/Pipeline vs. workspace code analysis). Ask for minimal missing inputs.
- Discover: Use MCP to fetch definitions and/or scan workspace code and metadata.
- Synthesize: Create a minimal, valid bundle with resources.jobs and/or resources.pipelines, shared clusters if needed, targets.dev, variables, and artifacts when applicable.
- Validate: Run databricks bundle validate and fix errors.
- Deploy: Run databricks bundle deploy -t dev after user confirmation.
- Deliver: Produce a ready-to-run directory with README and clear next steps.


### Generate from existing Job

- Fetch full Job settings (including tasks, clusters, schedules, permissions).
- Prefer referencing names over opaque IDs when allowed; where IDs are required, keep them as-is.
- If the Job defines new_cluster, either:
    - Inline under the Job’s job_clusters with a job_cluster_key, or
    - Promote to resources.clusters and reference by key.
- Extract libraries, task parameters, and environment (spark_version, node_type, policy, init scripts).
- Create variables for any environment-specific values (paths, instance profiles, external locations).
- Map secrets to secret references, not literal values.


### Generate from existing Pipeline

- Fetch Pipeline configuration (clusters, libraries, configuration).
- Include libraries as bundle artifacts or direct workspace paths.
- Preserve edition, channel, photon, and expected trigger settings.
- Parameterize storage locations and path-like config fields via variables where practical.


### Generate from workspace code

- Scan selected paths to identify entry points:
    - DLT pipelines (look for dlt usage or pipeline settings)
    - Notebook jobs (notebooks ending with .py or .ipynb)
    - Python/SQL tasks, wheels, or requirements.txt
- Infer:
    - One or more jobs with tasks mapped to detected notebooks/entrypoints
    - Shared cluster or job-specific clusters (keep minimal, default to serverless or a small runtime if unspecified)
    - Artifacts section if building wheels or packaging local code
- Add variables for external resources and absolute paths.


### Bundle skeleton to emit

Use this as a minimal template; expand only as needed by the discovered resources.

```yaml
bundle:
  name: {{BUNDLE_NAME}}

variables:
  project_root:
    description: Base workspace path for code
    default: /Workspace/Repos/your-org/your-repo
  default_storage_location:
    description: External storage or base path for outputs
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
      schedule: null

  pipelines:
    {{PIPELINE_KEY}}:
      name: {{BUNDLE_NAME}} - dev pipeline
      clusters:
        - label: default
          num_workers: 1
      libraries: []
      configuration:
        pipeline_storage: ${var.default_storage_location}
```


### Recommended project layout

- bundles/{{BUNDLE_NAME}}/bundle.yml
- bundles/{{BUNDLE_NAME}}/resources/jobs.yml (optional split)
- bundles/{{BUNDLE_NAME}}/resources/pipelines.yml (optional split)
- bundles/{{BUNDLE_NAME}}/README.md
- .gitignore (exclude build/outputs as needed)


### Validation and deployment

- Run:
    - databricks bundle validate
    - databricks bundle deploy -t dev
- If validation fails, update bundle.yml to address missing fields, bad IDs, or unsupported settings.
- Optionally, run a smoke test:
    - databricks bundle run {{JOB_KEY}} -t dev
    - Or trigger the pipeline run if applicable.


### Quality checks

- Minimal first: only include resources that exist and are needed.
- Prefer variables for anything workspace-specific or path-like.
- Do not embed secrets; use secret scopes or reference variables.
- Keep names consistent; use kebab-case keys and readable resource names.
- Include a short README with how to validate, deploy, and where to edit.


### Example README content

```markdown
# {{BUNDLE_NAME}} (dev)

Commands:
- Validate: `databricks bundle validate`
- Deploy (dev): `databricks bundle deploy -t dev`

Edit bundle settings in `bundle.yml`. Update variables under `variables:` or set via environment/CLI.
```


### When to ask for help

- Missing workspace host/profile or ambiguous source selection.
- Conflicting or incomplete Job/Pipeline definitions.
- Required cluster policy/runtime not provided.
- Permission or API errors from MCP/CLI.

***

Would you like the default flow to prioritize “generate from existing Job/Pipeline” when both code and existing resources are available, and what workspace host/profile should be set for the dev target?