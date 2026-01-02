# Quick Start Guide

## Prerequisites

1. **Azure DevOps Account**: You need an Azure DevOps organization and project
2. **Personal Access Token (PAT)**: Create a PAT with Variable Groups permissions
3. **Python 3.8+**: Required for running Ansible
4. **Ansible 2.13+**: Install via `pip install ansible`

## Installation Steps

### 1. Install the Collection

```bash
# Install from Ansible Galaxy (when published)
ansible-galaxy collection install basicPr0grammer.azure_devops

# OR install from source
cd /Users/basicPr0grammer/Desktop/ansible_galaxy_project
ansible-galaxy collection build
ansible-galaxy collection install basicPr0grammer-azure_devops-1.0.0.tar.gz --force
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install directly:

```bash
pip install azure-devops
```

### 3. Set Up Authentication

Create a Personal Access Token in Azure DevOps:

1. Go to https://dev.azure.com/{your-organization}
2. Click on User Settings (top right) → Personal Access Tokens
3. Click "+ New Token"
4. Set the following:
   - Name: "Ansible Automation"
   - Organization: Select your organization
   - Expiration: Set as needed
   - Scopes: Custom defined → Variable Groups (Read, create & manage)
5. Click "Create" and **copy the token** (you won't see it again!)

Export the token as an environment variable:

```bash
export AZURE_DEVOPS_PAT="your-pat-token-here"
export ADO_ORGANIZATION="your-org-name"
export ADO_PROJECT="your-project-name"
```

### 4. Create Your First Playbook

Create `my-playbook.yml`:

```yaml
---
- name: My First Azure DevOps Automation
  hosts: localhost
  gather_facts: false
  
  tasks:
    - name: Create a variable group
      basicPr0grammer.azure_devops.azure_devops_variable_group:
        organization: "{{ lookup('env', 'ADO_ORGANIZATION') }}"
        project: "{{ lookup('env', 'ADO_PROJECT') }}"
        personal_access_token: "{{ lookup('env', 'AZURE_DEVOPS_PAT') }}"
        name: "my-first-group"
        description: "My first variable group"
        variables:
          HELLO: "world"
          ENVIRONMENT: "test"
        state: present
```

### 5. Run the Playbook

```bash
ansible-playbook my-playbook.yml
```

### 6. Verify in Azure DevOps

1. Go to your Azure DevOps project
2. Navigate to Pipelines → Library
3. You should see "my-first-group" in the Variable Groups list

## Testing the Collection

### Run Integration Tests

```bash
# Set environment variables
export AZURE_DEVOPS_PAT="your-pat"
export ADO_ORGANIZATION="your-org"
export ADO_PROJECT="your-project"

# Run tests
ansible-playbook tests/integration/targets/azure_devops_variable_group/tasks/main.yml
```

### Use Check Mode

Test changes without applying them:

```bash
ansible-playbook my-playbook.yml --check
```

## Common Use Cases

### 1. Environment Configuration Management

```yaml
- name: Setup environment configs
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    name: "{{ item.name }}"
    description: "{{ item.env }} environment variables"
    variables: "{{ item.vars }}"
    state: present
  loop:
    - name: "dev-config"
      env: "Development"
      vars:
        ENV: "dev"
        DEBUG: "true"
    - name: "prod-config"
      env: "Production"
      vars:
        ENV: "prod"
        DEBUG: "false"
```

### 2. Secret Management

```yaml
- name: Store application secrets
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    name: "app-secrets"
    variables:
      DB_PASSWORD:
        value: "{{ vault_db_password }}"
        is_secret: true
      API_KEY:
        value: "{{ vault_api_key }}"
        is_secret: true
    state: present
  no_log: true
```

### 3. Dynamic Variable Groups

```yaml
- name: Create variable groups from configuration file
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    name: "{{ item.key }}"
    description: "Auto-generated from config"
    variables: "{{ item.value }}"
    state: present
  loop: "{{ lookup('file', 'configs.json') | from_json | dict2items }}"
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check the [example playbook](playbook-example.yml) for more examples
- Explore the module documentation: `ansible-doc basicPr0grammer.azure_devops.azure_devops_variable_group`

## Troubleshooting

### Authentication Errors

```
Error: Failed to connect to Azure DevOps
```

**Solution**: Verify your PAT has the correct permissions and hasn't expired.

### Module Not Found

```
Error: couldn't resolve module/action 'basicPr0grammer.azure_devops.azure_devops_variable_group'
```

**Solution**: Ensure the collection is properly installed:
```bash
ansible-galaxy collection list | grep azure_devops
```

### Import Errors

```
Error: No module named 'azure.devops'
```

**Solution**: Install Python dependencies:
```bash
pip install azure-devops
```

## Support

- GitHub Issues: https://github.com/basicPr0grammer/ansible-azure-devops/issues
- Discussions: https://github.com/basicPr0grammer/ansible-azure-devops/discussions
