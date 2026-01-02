# Service Endpoint Types - Quick Reference

This document provides examples for all supported service endpoint types.

## 1. Generic API Endpoint

For connecting to any REST API with basic authentication.

```yaml
- name: Generic API endpoint
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "my-api"
    description: "External API connection"
    endpoint_type: "generic"
    url: "https://api.example.com"
    authorization:
      scheme: "UsernamePassword"
      parameters:
        username: "api-user"
        password: "{{ api_password }}"
    state: present
```

**Common uses:**
- External REST APIs
- Custom services
- Third-party integrations

---

## 2. GitHub

For connecting to GitHub repositories.

```yaml
- name: GitHub connection
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "github-connection"
    description: "GitHub repositories"
    endpoint_type: "github"
    url: "https://github.com"
    authorization:
      scheme: "PersonalAccessToken"
      parameters:
        accessToken: "{{ github_token }}"
    state: present
```

**Required GitHub token scopes:**
- `repo` - Full control of private repositories
- `admin:repo_hook` - Full control of repository hooks

---

## 3. Docker Registry

For connecting to Docker registries (Docker Hub, ACR, ECR, etc.)

### Docker Hub

```yaml
- name: Docker Hub
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "docker-hub"
    description: "Docker Hub registry"
    endpoint_type: "dockerregistry"
    url: "https://index.docker.io/v1/"
    authorization:
      scheme: "UsernamePassword"
      parameters:
        username: "{{ docker_username }}"
        password: "{{ docker_password }}"
        email: "{{ docker_email }}"
        registry: "https://index.docker.io/v1/"
    state: present
```

### Azure Container Registry (ACR)

```yaml
- name: Azure Container Registry
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "acr-prod"
    description: "Production ACR"
    endpoint_type: "dockerregistry"
    url: "myregistry.azurecr.io"
    authorization:
      scheme: "UsernamePassword"
      parameters:
        username: "{{ acr_username }}"
        password: "{{ acr_password }}"
        email: "devops@example.com"
        registry: "myregistry.azurecr.io"
    state: present
```

### Private Docker Registry

```yaml
- name: Private registry
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "private-registry"
    description: "Private Docker registry"
    endpoint_type: "dockerregistry"
    url: "registry.company.com:5000"
    authorization:
      scheme: "UsernamePassword"
      parameters:
        username: "{{ registry_user }}"
        password: "{{ registry_pass }}"
        email: "devops@company.com"
        registry: "registry.company.com:5000"
    state: present
```

---

## 4. Azure Resource Manager (Azure Subscription)

For connecting to Azure subscriptions using Service Principal.

```yaml
- name: Azure Production Subscription
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "azure-prod"
    description: "Production Azure subscription"
    endpoint_type: "azurerm"
    url: "https://management.azure.com/"
    authorization:
      scheme: "ServicePrincipal"
      parameters:
        tenantid: "{{ azure_tenant_id }}"
        serviceprincipalid: "{{ service_principal_id }}"
        authenticationType: "spnKey"
        serviceprincipalkey: "{{ service_principal_key }}"
    data:
      subscriptionId: "{{ azure_subscription_id }}"
      subscriptionName: "Production Subscription"
      environment: "AzureCloud"  # or AzureUSGovernment, AzureChinaCloud, AzureGermanCloud
      scopeLevel: "Subscription"
      creationMode: "Manual"
    state: present
```

**How to create Azure Service Principal:**

```bash
# Login to Azure
az login

# Create Service Principal
az ad sp create-for-rbac --name "MyAzureDevOpsSP" --role contributor \
  --scopes /subscriptions/{subscription-id}

# Output will contain:
# - appId (serviceprincipalid)
# - password (serviceprincipalkey)
# - tenant (tenantid)
```

**Required Azure permissions:**
- Contributor role on the subscription (or specific resource groups)

---

## 5. Kubernetes

For connecting to Kubernetes clusters using service account token.

```yaml
- name: Kubernetes cluster (Token-based)
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "k8s-prod"
    description: "Production Kubernetes cluster"
    endpoint_type: "kubernetes"
    url: "https://k8s-cluster.example.com:6443"
    authorization:
      scheme: "Token"
      parameters:
        apitoken: "{{ k8s_service_account_token }}"
    data:
      authorizationType: "ServiceAccount"
      acceptUntrustedCerts: "true"
    state: present
```

**Alternative: Kubeconfig-based**

```yaml
- name: Kubernetes with kubeconfig
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "k8s-prod"
    description: "Production Kubernetes cluster"
    endpoint_type: "kubernetes"
    url: "https://k8s-cluster.example.com:6443"
    authorization:
      scheme: "Kubeconfig"
      parameters:
        kubeconfig: "{{ k8s_kubeconfig_content }}"
    data:
      authorizationType: "Kubeconfig"
    state: present
```

**How to get Kubernetes service account token:**

```bash
# Create a service account
kubectl create serviceaccount azure-devops-sa

# Create a cluster role binding
kubectl create clusterrolebinding azure-devops-sa-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=default:azure-devops-sa

# Get the token (Kubernetes 1.24+)
kubectl create token azure-devops-sa

# Or for older versions:
kubectl get secret $(kubectl get serviceaccount azure-devops-sa -o jsonpath='{.secrets[0].name}') \
  -o jsonpath='{.data.token}' | base64 --decode
```

---

## Testing All Types

Run the comprehensive test to verify all endpoint types:

```bash
export AZURE_DEVOPS_PAT="your-pat"
export ADO_ORGANIZATION="your-org"
export ADO_PROJECT="your-project"

ansible-playbook tests/integration/targets/azure_devops_service_endpoint/tasks/comprehensive_test.yml
```

---

## Common Patterns

### Create Multiple Environments

```yaml
- name: Create service endpoints for all environments
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    personal_access_token: "{{ ado_pat }}"
    name: "azure-{{ item.env }}"
    description: "{{ item.env | title }} environment"
    endpoint_type: "azurerm"
    url: "https://management.azure.com/"
    authorization:
      scheme: "ServicePrincipal"
      parameters:
        tenantid: "{{ azure_tenant_id }}"
        serviceprincipalid: "{{ item.sp_id }}"
        serviceprincipalkey: "{{ item.sp_key }}"
    data:
      subscriptionId: "{{ item.sub_id }}"
      subscriptionName: "{{ item.env | title }}"
      environment: "AzureCloud"
    state: present
  loop:
    - { env: "dev", sp_id: "{{ dev_sp }}", sp_key: "{{ dev_key }}", sub_id: "{{ dev_sub }}" }
    - { env: "staging", sp_id: "{{ stg_sp }}", sp_key: "{{ stg_key }}", sub_id: "{{ stg_sub }}" }
    - { env: "prod", sp_id: "{{ prod_sp }}", sp_key: "{{ prod_key }}", sub_id: "{{ prod_sub }}" }
  no_log: true
```

### Conditional Creation

```yaml
- name: Create GitHub endpoint only if token is provided
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    personal_access_token: "{{ ado_pat }}"
    name: "github"
    endpoint_type: "github"
    url: "https://github.com"
    authorization:
      scheme: "PersonalAccessToken"
      parameters:
        accessToken: "{{ github_token }}"
    state: present
  when: github_token is defined and github_token | length > 0
```

### Update Existing Endpoint

```yaml
- name: Update endpoint description and URL
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "{{ ado_org }}"
    project: "{{ ado_project }}"
    personal_access_token: "{{ ado_pat }}"
    name: "existing-endpoint"
    description: "Updated description"
    endpoint_type: "generic"
    url: "https://new-api.example.com"
    authorization:
      scheme: "UsernamePassword"
      parameters:
        username: "user"
        password: "pass"
    state: present
```

---

## Troubleshooting

### Endpoint shows as "Not Ready"

If `is_ready: false`, check:
1. Credentials are correct
2. URL is accessible from Azure DevOps
3. Service has proper permissions

### Idempotency Issues

The module automatically handles:
- Secret parameters (won't trigger updates)
- Description changes
- URL changes
- Authorization scheme changes

### Permission Errors

Ensure your PAT has:
- **Service Connections**: Read, query & manage

---

## Security Best Practices

1. **Use Ansible Vault** for sensitive data:
   ```bash
   ansible-vault encrypt_string 'my-secret' --name 'api_password'
   ```

2. **Use environment variables**:
   ```yaml
   password: "{{ lookup('env', 'API_PASSWORD') }}"
   ```

3. **Use `no_log: true`** for sensitive tasks:
   ```yaml
   - name: Create endpoint
     azure_devops_service_endpoint:
       # ... with secrets
     no_log: true
   ```

4. **Rotate credentials regularly** - use the update functionality to rotate passwords/tokens

---

## Next Steps

- Explore the [full documentation](../README.md)
- Check [example playbooks](../examples/)
- Learn about [variable groups](azure_devops_variable_group.md)
