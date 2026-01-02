# Azure DevOps Pipeline Module Guide

## Overview

The `azure_devops_pipeline` module allows you to manage Azure DevOps pipelines programmatically. You can create pipelines that reference YAML files in your repositories, run pipelines with custom variables and branches, and manage the pipeline lifecycle.

## Key Features

- ✅ Create pipelines pointing to YAML files in repositories
- ✅ Organize pipelines in folders
- ✅ Run pipelines on-demand
- ✅ Specify branch for pipeline execution
- ✅ Pass variables and template parameters
- ✅ Wait for pipeline completion
- ✅ Delete pipelines
- ✅ Full idempotency support

## Basic Usage

### Creating a Pipeline

The most basic pipeline creation requires:
- Pipeline name
- Repository reference (ID or name)
- Path to YAML file in the repository

```yaml
- name: Create a simple pipeline
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    repository_name: "my-repo"
    yaml_path: "/azure-pipelines.yml"
    state: present
```

### Running a Pipeline

Once created, you can run the pipeline:

```yaml
- name: Run the pipeline
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    state: run
```

### Deleting a Pipeline

```yaml
- name: Delete the pipeline
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    state: absent
```

## Advanced Features

### Pipeline Folders

Organize pipelines into folders for better management:

```yaml
- name: Create pipeline in subfolder
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "frontend-build"
    folder: "\\Builds\\Frontend"
    repository_name: "frontend-repo"
    yaml_path: "/pipelines/build.yml"
    state: present
```

**Folder Path Format:**
- Root folder: `\\`
- Single level: `\\MyFolder`
- Multiple levels: `\\MyFolder\\SubFolder\\DeepFolder`

### Branch Selection

Run pipelines on specific branches:

```yaml
- name: Run pipeline on feature branch
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    branch: "feature/new-feature"
    state: run
```

**Branch Name Formats:**
- Simple name: `main`, `develop`, `feature/my-feature`
- Full ref: `refs/heads/main`, `refs/heads/feature/my-feature`

Both formats are accepted; simple names are automatically converted to full refs.

### Pipeline Variables

Pass runtime variables to your pipeline:

```yaml
- name: Run with custom variables
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    variables:
      BuildConfiguration: "Release"
      RunTests: "true"
      DeploymentTarget: "Production"
      Version: "1.2.3"
    state: run
```

These variables override any default values in your YAML pipeline and can be accessed using `$(VariableName)` syntax in your pipeline.

### Template Parameters

For pipelines using templates with parameters:

```yaml
- name: Run with template parameters
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-template-pipeline"
    template_parameters:
      environment: "production"
      region: "eastus"
      instanceCount: 3
    state: run
```

### Waiting for Completion

By default, the `run` state starts the pipeline and returns immediately. To wait for the pipeline to complete:

```yaml
- name: Run and wait for pipeline
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "deployment-pipeline"
    wait_for_completion: true
    wait_timeout: 1800  # 30 minutes
    state: run
  register: pipeline_result

- name: Check if deployment succeeded
  debug:
    msg: "Pipeline {{ pipeline_result.run.result }}"
  failed_when: pipeline_result.run.result != "succeeded"
```

**Wait Configuration:**
- `wait_for_completion: true` - Wait for pipeline to finish
- `wait_timeout: 600` - Maximum wait time in seconds (default: 600 = 10 minutes)

**Pipeline States:**
- `inProgress` - Currently running
- `completed` - Finished execution
- `canceling` - Being canceled
- `canceled` - Was canceled

**Pipeline Results (when completed):**
- `succeeded` - All jobs passed
- `failed` - One or more jobs failed
- `canceled` - Pipeline was canceled
- `partiallySucceeded` - Some jobs passed, some failed

## Complete Examples

### CI/CD Pipeline Setup

```yaml
---
- name: Setup complete CI/CD pipelines
  hosts: localhost
  vars:
    org_url: "https://dev.azure.com/myorg"
    project: "MyApp"
  
  tasks:
    # Create build pipeline
    - name: Create build pipeline
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "app-build"
        folder: "\\CI"
        repository_name: "my-app"
        yaml_path: "/pipelines/build.yml"
        state: present
      register: build_pipeline
    
    # Create deployment pipelines for each environment
    - name: Create deployment pipelines
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "app-deploy-{{ item }}"
        folder: "\\CD\\{{ item | title }}"
        repository_name: "my-app"
        yaml_path: "/pipelines/deploy.yml"
        state: present
      loop:
        - dev
        - staging
        - production
    
    # Run build
    - name: Trigger build
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "app-build"
        branch: "main"
        variables:
          BuildConfiguration: "Release"
          VersionSuffix: "{{ ansible_date_time.epoch }}"
        wait_for_completion: true
        wait_timeout: 900
        state: run
      register: build_result
    
    # Deploy to dev if build succeeded
    - name: Deploy to dev
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "app-deploy-dev"
        variables:
          BuildId: "{{ build_result.run.id }}"
          Environment: "dev"
        state: run
      when: build_result.run.result == "succeeded"
```

### Multi-Branch Pipeline Management

```yaml
---
- name: Manage feature branch pipelines
  hosts: localhost
  vars:
    org_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    branches:
      - main
      - develop
      - feature/auth
      - feature/api-v2
  
  tasks:
    # Create pipeline for each branch
    - name: Ensure pipelines exist
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "build-{{ item | replace('/', '-') }}"
        folder: "\\Branches"
        repository_name: "my-app"
        yaml_path: "/azure-pipelines.yml"
        state: present
      loop: "{{ branches }}"
    
    # Run all branch pipelines
    - name: Run pipeline for each branch
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "build-{{ item | replace('/', '-') }}"
        branch: "{{ item }}"
        variables:
          BranchName: "{{ item }}"
        state: run
      loop: "{{ branches }}"
```

### Conditional Pipeline Execution

```yaml
---
- name: Conditional pipeline runs
  hosts: localhost
  vars:
    org_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    current_hour: "{{ ansible_date_time.hour | int }}"
  
  tasks:
    # Run integration tests only during business hours
    - name: Run integration tests
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "integration-tests"
        state: run
      when: current_hour >= 9 and current_hour <= 17
    
    # Run heavy load tests only at night
    - name: Run load tests
      azure_devops_pipeline:
        organization_url: "{{ org_url }}"
        project: "{{ project }}"
        name: "load-tests"
        variables:
          TestDuration: "3600"
          ConcurrentUsers: "1000"
        state: run
      when: current_hour >= 22 or current_hour <= 6
```

## Repository Types

The module supports various repository types:

### Azure Repos Git

```yaml
- name: Pipeline for Azure Repos
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-pipeline"
    repository_name: "my-repo"
    repository_type: "azureReposGit"  # Default
    yaml_path: "/pipelines/build.yml"
    state: present
```

### GitHub

```yaml
- name: Pipeline for GitHub repo
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "github-pipeline"
    repository_id: "owner/repo-name"
    repository_type: "github"
    yaml_path: "/.azure-pipelines/build.yml"
    state: present
```

**Note:** For GitHub repositories, you'll need a GitHub service connection configured in your Azure DevOps project.

## Return Values

### When state is 'present' or 'run'

```yaml
pipeline:
  id: 123
  name: "my-build-pipeline"
  folder: "\\Builds"
  revision: 1
  url: "https://dev.azure.com/myorg/MyProject/_apis/pipelines/123"
```

### When state is 'run'

```yaml
run:
  id: 456
  name: "20240101.1"
  state: "completed"
  result: "succeeded"
  url: "https://dev.azure.com/myorg/MyProject/_build/results?buildId=456"
  created_date: "2024-01-01T10:00:00Z"
  finished_date: "2024-01-01T10:15:00Z"
```

## Error Handling

```yaml
- name: Run pipeline with error handling
  azure_devops_pipeline:
    organization_url: "{{ org_url }}"
    project: "{{ project }}"
    name: "risky-pipeline"
    wait_for_completion: true
    state: run
  register: result
  ignore_errors: true

- name: Handle failure
  debug:
    msg: "Pipeline failed: {{ result.msg }}"
  when: result.failed

- name: Handle success but bad result
  debug:
    msg: "Pipeline completed but {{ result.run.result }}"
  when: 
    - not result.failed
    - result.run.result != "succeeded"
```

## Best Practices

### 1. Use Environment Variables for Credentials

```bash
export AZURE_DEVOPS_PAT="your-token-here"
```

```yaml
- name: Create pipeline
  azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-pipeline"
    # PAT automatically read from environment
    repository_name: "my-repo"
    yaml_path: "/pipelines/build.yml"
    state: present
```

### 2. Register and Check Results

```yaml
- name: Run deployment
  azure_devops_pipeline:
    organization_url: "{{ org_url }}"
    project: "{{ project }}"
    name: "deploy-production"
    wait_for_completion: true
    state: run
  register: deployment

- name: Verify deployment
  assert:
    that:
      - deployment.run.result == "succeeded"
    fail_msg: "Deployment failed!"
    success_msg: "Deployment successful!"
```

### 3. Use Variables for Common Parameters

```yaml
---
- hosts: localhost
  vars:
    azure_devops:
      organization_url: "https://dev.azure.com/myorg"
      project: "MyProject"
  
  tasks:
    - name: Create pipeline
      azure_devops_pipeline:
        organization_url: "{{ azure_devops.organization_url }}"
        project: "{{ azure_devops.project }}"
        name: "my-pipeline"
        repository_name: "my-repo"
        yaml_path: "/pipelines/build.yml"
        state: present
```

### 4. Organize Pipelines Logically

```yaml
# Use consistent folder structure
CI Pipelines: \\CI\\ComponentName
CD Pipelines: \\CD\\Environment\\ComponentName
Test Pipelines: \\Tests\\TestType
Maintenance: \\Maintenance
```

### 5. Use Tags or Naming Conventions

```yaml
- name: Create environment-specific pipelines
  azure_devops_pipeline:
    organization_url: "{{ org_url }}"
    project: "{{ project }}"
    name: "{{ app_name }}-{{ env }}-deploy"
    folder: "\\Deployments\\{{ env | title }}"
    repository_name: "{{ app_name }}"
    yaml_path: "/deploy/{{ env }}.yml"
    state: present
  vars:
    app_name: "my-app"
  loop:
    - dev
    - staging
    - production
  loop_control:
    loop_var: env
```

## Troubleshooting

### Pipeline Not Found

```
Error: Pipeline 'my-pipeline' not found in folder '\\'
```

**Solution:** Ensure the pipeline name and folder match exactly. Pipeline lookups are case-sensitive.

### Repository Not Found

```
Error: Repository 'my-repo' not found
```

**Solution:** 
- Verify the repository exists in the specified project
- Use repository ID instead of name
- Check repository name spelling

### YAML Path Invalid

```
Error: Failed to create pipeline: The pipeline configuration path '/wrong-path.yml' does not exist
```

**Solution:** 
- Verify the YAML file exists in the repository
- Check the path starts with `/`
- Ensure the branch contains the YAML file (defaults to main branch)

### Permission Denied

```
Error: Access Denied: User does not have permission to create pipelines
```

**Solution:** Ensure your PAT has the following scopes:
- **Build** (Read & Execute)
- **Code** (Read) - for accessing repository information

### Wait Timeout

```
Error: Pipeline run timed out after 600 seconds
```

**Solution:**
- Increase `wait_timeout` parameter
- Check if pipeline is stuck or taking longer than expected
- Consider not waiting and checking status separately

## Limitations

1. **No Direct Update**: Pipelines don't support direct updates via API. To change pipeline configuration (like folder or YAML path), you need to delete and recreate the pipeline.

2. **Branch Must Exist**: When running a pipeline on a specific branch, that branch must exist in the repository.

3. **YAML Required**: All pipelines must reference a YAML file in a repository. Classic (UI-based) pipelines are not supported by this module.

4. **Repository Access**: The service account must have read access to the repository containing the pipeline YAML.

## See Also

- [Azure DevOps Pipeline Documentation](https://docs.microsoft.com/en-us/azure/devops/pipelines/)
- [YAML Schema Reference](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema/)
- [Pipeline Variables](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/variables)
