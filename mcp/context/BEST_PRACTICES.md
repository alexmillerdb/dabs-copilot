# Best Practices (Essential)

## Naming
- Bundle: descriptive-kebab-case
- Jobs: ${bundle.name}-${bundle.target}
- Resources: snake_case keys

## Configuration
- Use job clusters, not existing clusters
- Add email_notifications for all jobs
- Set timeout_seconds and max_retries
- Use ${var.catalog} for Unity Catalog

## Security
- Never hardcode secrets - use ${secrets.scope.key}
- Add permissions for production jobs
- Use service principals in prod

## Environment Patterns
```yaml
targets:
  dev:
    mode: development
    # Smaller clusters, paused schedules
  prod:  
    mode: production
    # Full clusters, active schedules
```

## Required Fields
- bundle.name
- resources.jobs
- job.name, job.tasks
- task.task_key, task.job_cluster_key