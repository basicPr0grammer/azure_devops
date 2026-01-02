# Ansible Collection - basicPr0grammer.azure_devops

An Ansible collection for managing Azure DevOps resources using the Azure DevOps Python SDK.

## Description

This collection provides modules to interact with Azure DevOps services, allowing you to automate the management of your Azure DevOps infrastructure using Ansible playbooks.

Currently supported resources:
- **Repositories**: Manage Git repositories including creation, disable/enable, forking, and branch operations
- **Pipelines**: Create, delete, and run Azure DevOps pipelines with branch selection and variable support
- **Environments**: Manage Azure DevOps environments with approvers and permissions
- **Service Endpoints**: Manage service connections for Azure RM, GitHub, Docker Registry, Kubernetes, and generic endpoints
- **Branch Policies**: Configure branch protection policies including reviewers, work item linking, comment resolution, and build validation
- **Pipeline Approvals**: Approve or reject pipeline runs waiting for manual approval in environments
- **Variable Groups**: Create, update, and delete variable groups with support for both plain text and secret variables
- **Work Items**: Create, update, and delete work items with full field support and parent-child linking
- **Agent Pools**: List and monitor Azure DevOps agent pools and their agents
- **Service Hooks**: Manage webhooks for Azure DevOps events (work items, pull requests, builds, deployments)

## Requirements

- Python >= 3.8
- ansible-core >= 2.13
- azure-devops >= 7.1.0
- An Azure DevOps organization and Personal Access Token (PAT)

## Installation

### Install from Ansible Galaxy

```bash
ansible-galaxy collection install basicPr0grammer.azure_devops
```

### Install from source

```bash
git clone https://github.com/basicPr0grammer/ansible-azure-devops.git
cd ansible-azure-devops
ansible-galaxy collection build
ansible-galaxy collection install basicPr0grammer-azure_devops-*.tar.gz
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

Or install the collection with dependencies:

```bash
ansible-galaxy collection install basicPr0grammer.azure_devops
pip install azure-devops
```

## Authentication

All modules require authentication to Azure DevOps. You can provide credentials in two ways:

1. **Module parameter**: Pass `personal_access_token` directly to the module
2. **Environment variable**: Set `AZURE_DEVOPS_PAT` environment variable

### Creating a Personal Access Token (PAT)

1. Sign in to your Azure DevOps organization
2. Go to User Settings > Personal Access Tokens
3. Create a new token with appropriate scopes:
   - For repositories: **Code (Read, Write & Manage)**
   - For pipelines: **Build (Read & Execute)**
   - For environments: **Environment (Read & Manage)**
   - For service endpoints: **Service Connections (Read, Query & Manage)**
   - For branch policies: **Code (Read, Write & Manage)**
   - For pipeline approvals: **Build (Read & Execute)**
   - For variable groups: **Variable Groups (Read, Create & Manage)**
   - For work items: **Work Items (Read, Write & Manage)**
   - For agent pools: **Agent Pools (Read)** (Create requires organization admin)
   - For service hooks: **Service Hooks (Read, Query & Manage)**
4. Copy the token and store it securely

## Usage

### Basic Example

```yaml
- name: Manage Azure DevOps Variable Groups
  hosts: localhost
  collections:
    - basicPr0grammer.azure_devops
  
  vars:
    ado_org: "myorganization"
    ado_project: "myproject"
    ado_pat: "{{ lookup('env', 'AZURE_DEVOPS_PAT') }}"
  
  tasks:
    - name: Create a variable group
      azure_devops_variable_group:
        organization: "{{ ado_org }}"
        project: "{{ ado_project }}"
        personal_access_token: "{{ ado_pat }}"
        name: "production-variables"
        description: "Production environment variables"
        variables:
          ENVIRONMENT: "production"
          APP_URL: "https://app.example.com"
          DEBUG_MODE: "false"
        state: present
```

### Working with Secrets

```yaml
- name: Create variable group with secrets
  azure_devops_variable_group:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    personal_access_token: "{{ ado_pat }}"
    name: "application-secrets"
    description: "Sensitive application credentials"
    variables:
      # Regular variable
      API_ENDPOINT: "https://api.example.com"
      
      # Secret variables
      API_KEY:
        value: "{{ api_key }}"
        is_secret: true
      
      DATABASE_PASSWORD:
        value: "{{ db_password }}"
        is_secret: true
      
      ENCRYPTION_KEY:
        value: "{{ encryption_key }}"
        is_secret: true
    state: present
```

### Updating Variables

```yaml
- name: Update existing variable group
  azure_devops_variable_group:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    personal_access_token: "{{ ado_pat }}"
    name: "production-variables"
    variables:
      ENVIRONMENT: "production"
      APP_URL: "https://new-app.example.com"  # Updated value
      NEW_SETTING: "enabled"  # New variable
    state: present
```

### Deleting Variable Groups

```yaml
- name: Delete variable group
  azure_devops_variable_group:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    personal_access_token: "{{ ado_pat }}"
    name: "old-variable-group"
    state: absent
```

### Using Environment Variables for Authentication

```yaml
# Set environment variable
export AZURE_DEVOPS_PAT="your-pat-here"

# In your playbook
- name: Create variable group (PAT from env)
  azure_devops_variable_group:
    organization: "myorg"
    project: "myproject"
    name: "my-variables"
    variables:
      KEY: "value"
    state: present
```

## Modules

### azure_devops_variable_group

Manage Azure DevOps Variable Groups.

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| organization | yes | str | - | Azure DevOps organization name |
| project | yes | str | - | Project name or ID |
| personal_access_token | no | str | - | PAT for authentication (or use AZURE_DEVOPS_PAT env var) |
| name | yes | str | - | Variable group name |
| description | no | str | "" | Variable group description |
| variables | no | dict | {} | Dictionary of variables |
| state | no | str | present | Desired state (present/absent) |

**Variable Format:**

Variables can be specified in two formats:

1. **Simple format** (plain text variables):
   ```yaml
   variables:
     VAR_NAME: "value"
   ```

2. **Extended format** (with secret support):
   ```yaml
   variables:
     VAR_NAME:
       value: "the-value"
       is_secret: true
   ```

### azure_devops_service_endpoint

Manage Azure DevOps Service Endpoints (Service Connections).

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| organization | yes | str | - | Azure DevOps organization name |
| project | yes | str | - | Project name or ID |
| personal_access_token | no | str | - | PAT for authentication (or use AZURE_DEVOPS_PAT env var) |
| name | yes | str | - | Service endpoint name |
| description | no | str | "" | Service endpoint description |
| endpoint_type | no | str | generic | Type of endpoint (azurerm, github, dockerregistry, generic, kubernetes) |
| url | no | str | "" | Endpoint URL |
| authorization | no | dict | {} | Authorization configuration (scheme and parameters) |
| data | no | dict | {} | Additional endpoint-specific data |
| state | no | str | present | Desired state (present/absent) |

**Authorization Schemes:**

Different endpoint types support different authorization schemes:

1. **Azure RM** (endpoint_type: azurerm):
   ```yaml
   authorization:
     scheme: "ServicePrincipal"
     parameters:
       tenantid: "{{ azure_tenant_id }}"
       serviceprincipalid: "{{ sp_id }}"
       authenticationType: "spnKey"
       serviceprincipalkey: "{{ sp_key }}"
   data:
     subscriptionId: "{{ subscription_id }}"
     subscriptionName: "My Subscription"
     environment: "AzureCloud"
   ```

2. **GitHub** (endpoint_type: github):
   ```yaml
   authorization:
     scheme: "PersonalAccessToken"
     parameters:
       accessToken: "{{ github_token }}"
   ```

3. **Docker Registry** (endpoint_type: dockerregistry):
   ```yaml
   authorization:
     scheme: "UsernamePassword"
     parameters:
       username: "{{ docker_user }}"
       password: "{{ docker_pass }}"
       email: "{{ email }}"
       registry: "https://index.docker.io/v1/"
   ```

4. **Generic/API** (endpoint_type: generic):
   ```yaml
   authorization:
     scheme: "UsernamePassword"
     parameters:
       username: "{{ api_user }}"
       password: "{{ api_pass }}"
   ```

### azure_devops_pipeline

Manage Azure DevOps Pipelines (Build and Release pipelines).

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| organization_url | yes | str | - | Full Azure DevOps organization URL |
| project | yes | str | - | Project name or ID |
| personal_access_token | no | str | - | PAT for authentication (or use AZURE_DEVOPS_PAT env var) |
| name | yes | str | - | Pipeline name |
| folder | no | str | \\ | Folder path for the pipeline (e.g., '\\MyFolder') |
| state | no | str | present | Desired state (present/absent/run) |
| repository_id | no | str | - | Repository ID (required for creation) |
| repository_name | no | str | - | Repository name (alternative to repository_id) |
| repository_type | no | str | azureReposGit | Repository type |
| yaml_path | no | str | - | Path to pipeline YAML file (required for creation) |
| branch | no | str | - | Branch to run pipeline on (for state=run) |
| variables | no | dict | - | Variables to pass to pipeline run |
| template_parameters | no | dict | - | Template parameters for pipeline run |
| wait_for_completion | no | bool | false | Wait for pipeline run to complete |
| wait_timeout | no | int | 600 | Timeout in seconds when waiting |

**Return Values:**

| Field | Type | Description |
|-------|------|-------------|
| pipeline | dict | Pipeline details (id, name, folder, revision, url) |
| run | dict | Run details when state=run (id, name, state, result, url) |
| changed | bool | Whether changes were made |

**Examples:**

1. **Create a pipeline**:
   ```yaml
   - name: Create build pipeline
     azure_devops_pipeline:
       organization_url: "https://dev.azure.com/myorg"
       project: "MyProject"
       name: "my-app-build"
       folder: "\\Builds"
       repository_name: "my-app-repo"
       yaml_path: "/azure-pipelines.yml"
       state: present
   ```

2. **Run a pipeline**:
   ```yaml
   - name: Run pipeline
     azure_devops_pipeline:
       organization_url: "https://dev.azure.com/myorg"
       project: "MyProject"
       name: "my-app-build"
       state: run
   ```

3. **Run pipeline with variables and branch**:
   ```yaml
   - name: Run pipeline on feature branch
     azure_devops_pipeline:
       organization_url: "https://dev.azure.com/myorg"
       project: "MyProject"
       name: "my-app-build"
       branch: "feature/new-feature"
       variables:
         BuildConfiguration: "Release"
         RunTests: "true"
       state: run
   ```

4. **Run pipeline and wait for completion**:
   ```yaml
   - name: Run and wait for deployment
     azure_devops_pipeline:
       organization_url: "https://dev.azure.com/myorg"
       project: "MyProject"
       name: "deployment-pipeline"
       wait_for_completion: true
       wait_timeout: 900
       state: run
     register: deployment
   
   - name: Check result
     debug:
       msg: "Deployment {{ deployment.run.result }}"
   ```

5. **Delete a pipeline**:
   ```yaml
   - name: Delete old pipeline
     azure_devops_pipeline:
       organization_url: "https://dev.azure.com/myorg"
       project: "MyProject"
       name: "legacy-pipeline"
       state: absent
   ```

**Note:** The `organization_url` parameter expects the full URL (e.g., `https://dev.azure.com/myorg`) unlike other modules that use just the organization name. This is due to the Pipelines API design.

### azure_devops_repository

Manage Azure DevOps Git repositories including creation, forking, and branch operations.

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| organization_url | yes | str | - | Azure DevOps organization URL |
| project | yes | str | - | Project name or ID |
| personal_access_token | no | str | - | PAT for authentication |
| name | yes | str | - | Repository name |
| state | no | str | present | Desired state (present/absent) |
| default_branch | no | str | - | Default branch name |
| is_disabled | no | bool | false | Whether repository is disabled |
| parent_repository_id | no | str | - | Parent repository ID for forking |
| branch_name | no | str | - | Branch name for branch operations |
| source_branch | no | str | - | Source branch to create from |
| branch_state | no | str | - | Branch state (present/absent) |

**Examples:**

```yaml
# Create a repository
- name: Create new repository
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-new-repo"
    state: present

# Fork a repository
- name: Fork repository
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "forked-repo"
    parent_repository_id: "{{ source_repo_id }}"
    state: present

# Create a branch
- name: Create feature branch from main
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-repo"
    branch_name: "feature/new-feature"
    source_branch: "main"
    branch_state: present
    state: present

# Delete a branch
- name: Delete merged feature branch
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-repo"
    branch_name: "feature/old-feature"
    branch_state: absent
    state: present
```

### azure_devops_branch_policy

Configure branch protection policies for Azure DevOps repositories.

**Parameters:**

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| organization_url | yes | str | - | Azure DevOps organization URL |
| project | yes | str | - | Project name or ID |
| repository_id | yes | str | - | Repository ID to apply policy to |
| branch_name | yes | str | - | Branch name to protect |
| policy_type | yes | str | - | Policy type (minimum_reviewers, work_item_linking, comment_resolution, build_validation, required_reviewers, merge_strategy) |
| state | no | str | present | Desired state (present/absent) |
| is_blocking | no | bool | true | Whether policy blocks completion |
| is_enabled | no | bool | true | Whether policy is enabled |
| minimum_approver_count | no | int | - | Minimum number of reviewers (minimum_reviewers) |
| creator_vote_counts | no | bool | false | Creator can approve own PR (minimum_reviewers) |
| reset_on_source_push | no | bool | true | Reset votes on new commits (minimum_reviewers) |
| build_definition_id | no | int | - | Build pipeline ID (build_validation) |
| build_display_name | no | str | - | Policy display name (build_validation) |
| build_valid_duration | no | int | 720 | Build validity in minutes (build_validation) |

**Policy Types:**

1. **minimum_reviewers** - Require minimum number of reviewers to approve PR
2. **work_item_linking** - Require work items linked to PR
3. **comment_resolution** - All comments must be resolved before merge
4. **build_validation** - Require successful build before merge
5. **required_reviewers** - Specific reviewers required for file patterns
6. **merge_strategy** - Enforce merge strategy (squash, etc.)

**Examples:**

```yaml
# Require 2 reviewers for main branch
- name: Configure minimum reviewers policy
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: minimum_reviewers
    state: present
    is_blocking: true
    minimum_approver_count: 2
    creator_vote_counts: false
    reset_on_source_push: true

# Require work item linking (warning only)
- name: Configure work item policy
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: work_item_linking
    state: present
    is_blocking: false

# Require build validation
- name: Configure build validation
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: build_validation
    state: present
    build_definition_id: 123
    build_display_name: "PR Build"
```

### azure_devops_work_item

Create, update, and delete Azure DevOps work items with full field support.

**Parameters:**

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| organization_url | yes | str | Azure DevOps organization URL |
| project | yes | str | Project name |
| work_item_id | no | int | Work item ID (for update/delete) |
| work_item_type | no | str | Work item type (User Story, Bug, Task, etc.) |
| title | no | str | Work item title |
| description | no | str | Work item description (supports HTML) |
| work_item_state | no | str | Work item state (New, Active, Resolved, Closed) |
| assigned_to | no | str | Assigned user email |
| area_path | no | str | Area path |
| iteration_path | no | str | Iteration path |
| tags | no | str | Comma-separated tags |
| priority | no | int | Priority (1-4) |
| severity | no | str | Severity for bugs |
| parent_work_item_id | no | int | Parent work item ID for linking |
| state | no | str | Desired state (present/absent) |

**Example:**

```yaml
# Create a User Story
- name: Create user story
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    work_item_type: "User Story"
    title: "Implement login feature"
    description: "As a user, I want to login so that I can access my account"
    tags: "authentication,security"
    priority: 1
    state: present
  register: user_story

# Create a linked Task
- name: Create task
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    work_item_type: "Task"
    title: "Design login UI"
    parent_work_item_id: "{{ user_story.work_item.id }}"
    state: present

# Update work item state
- name: Update work item
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    work_item_id: 12345
    work_item_state: "Active"
    state: present
```

### azure_devops_agent_pool

List and monitor Azure DevOps agent pools and their agents.

**Parameters:**

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| organization_url | yes | str | Azure DevOps organization URL |
| pool_id | no | int | Agent pool ID |
| name | no | str | Agent pool name |
| state | no | str | Operation mode (info) |
| list_agents | no | bool | Include agent details in response |

**Example:**

```yaml
# List all agent pools
- name: List all pools
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/myorg"
    state: info
  register: all_pools

# Get specific pool details
- name: Get Default pool
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/myorg"
    name: "Default"
    state: info
  register: default_pool

# Get pool with agent list
- name: Get pool with agents
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/myorg"
    name: "Default"
    state: info
    list_agents: true
  register: pool_info
```

### azure_devops_service_hook

Manage Azure DevOps Service Hooks (webhooks) for event notifications.

**Parameters:**

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| organization_url | yes | str | Azure DevOps organization URL |
| project | no | str | Project name |
| subscription_id | no | str | Subscription ID (for delete/info) |
| event_type | no | str | Event type (workitem.updated, git.pullrequest.created, etc.) |
| consumer_type | no | str | Consumer type (webHooks, slack, teams) |
| webhook_url | no | str | Webhook URL |
| work_item_type | no | str | Filter by work item type |
| area_path | no | str | Filter by area path |
| state | no | str | Desired state (present/absent/info) |

**Example:**

```yaml
# Create webhook for User Story updates
- name: Create work item webhook
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    event_type: workitem.updated
    consumer_type: webHooks
    webhook_url: "https://my-server.com/webhook"
    work_item_type: "User Story"
    state: present
  register: webhook

# Create webhook for pull requests
- name: Create PR webhook
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    event_type: git.pullrequest.created
    consumer_type: webHooks
    webhook_url: "https://my-server.com/webhook/pr"
    state: present

# List all webhooks
- name: List subscriptions
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/myorg"
    state: info
  register: all_hooks

# Delete webhook
- name: Delete webhook
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/myorg"
    subscription_id: "{{ webhook.subscription.id }}"
    state: absent
```

## Idempotency

All modules in this collection follow Ansible's idempotency principles:

- **Create**: Only creates if the resource doesn't exist
- **Update**: Only updates if values have changed
- **Delete**: Only deletes if the resource exists
- **Secrets**: Secrets are always marked as changed when provided (Azure doesn't return secret values)

## Check Mode

All modules support Ansible's check mode (`--check`), allowing you to preview changes without applying them:

```bash
ansible-playbook playbook.yml --check
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

GNU General Public License v3.0 or later

See [LICENSE](LICENSE) for the full text.

## Author

basicPr0grammer

## Support

For issues, questions, or contributions, please visit:
- GitHub: https://github.com/basicPr0grammer/ansible-azure-devops
- Issues: https://github.com/basicPr0grammer/ansible-azure-devops/issues
