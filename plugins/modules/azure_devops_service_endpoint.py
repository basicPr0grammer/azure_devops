#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, basicPr0grammer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_service_endpoint
short_description: Manage Azure DevOps Service Endpoints (Service Connections)
description:
  - Create, update, or delete Azure DevOps Service Endpoints.
  - Support for multiple endpoint types including Azure RM, GitHub, Docker Registry, and Generic.
  - Ensure idempotent operations following Ansible best practices.
version_added: "1.0.0"
author:
  - basicPr0grammer
options:
  organization:
    description:
      - The name of the Azure DevOps organization.
    required: true
    type: str
  project:
    description:
      - The name or ID of the Azure DevOps project.
    required: true
    type: str
  personal_access_token:
    description:
      - Personal Access Token (PAT) for authentication.
      - Can also be set via AZURE_DEVOPS_PAT environment variable.
    required: false
    type: str
    no_log: true
  name:
    description:
      - The name of the service endpoint.
    required: true
    type: str
  description:
    description:
      - Description of the service endpoint.
    required: false
    type: str
    default: ""
  endpoint_type:
    description:
      - The type of service endpoint.
    required: false
    type: str
    choices: ['azurerm', 'github', 'dockerregistry', 'generic', 'kubernetes']
    default: 'generic'
  url:
    description:
      - The URL of the service endpoint.
      - Required for most endpoint types.
    required: false
    type: str
  authorization:
    description:
      - Authorization parameters for the service endpoint.
      - Structure varies by endpoint type.
    required: false
    type: dict
    default: {}
  data:
    description:
      - Additional data specific to the endpoint type.
      - For Azure RM endpoints, includes subscription info.
    required: false
    type: dict
    default: {}
  state:
    description:
      - Whether the service endpoint should exist or not.
    choices: ['present', 'absent']
    default: present
    type: str
requirements:
  - azure-devops>=7.1.0
notes:
  - The PAT must have permissions to manage service endpoints.
  - Different endpoint types require different authorization parameters.
  - Azure RM endpoints require subscription details and service principal credentials.
'''

EXAMPLES = r'''
- name: Create a generic service endpoint
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "my-api-endpoint"
    description: "Connection to external API"
    endpoint_type: "generic"
    url: "https://api.example.com"
    authorization:
      scheme: "UsernamePassword"
      parameters:
        username: "api-user"
        password: "{{ api_password }}"
    state: present

- name: Create an Azure RM service endpoint
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "azure-production"
    description: "Azure Production Subscription"
    endpoint_type: "azurerm"
    url: "https://management.azure.com/"
    authorization:
      scheme: "ServicePrincipal"
      parameters:
        tenantid: "{{ azure_tenant_id }}"
        serviceprincipalid: "{{ azure_sp_id }}"
        authenticationType: "spnKey"
        serviceprincipalkey: "{{ azure_sp_key }}"
    data:
      subscriptionId: "{{ azure_subscription_id }}"
      subscriptionName: "Production Subscription"
      environment: "AzureCloud"
      scopeLevel: "Subscription"
      creationMode: "Manual"
    state: present

- name: Create a GitHub service endpoint
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "github-connection"
    description: "GitHub Connection"
    endpoint_type: "github"
    url: "https://github.com"
    authorization:
      scheme: "PersonalAccessToken"
      parameters:
        accessToken: "{{ github_token }}"
    state: present

- name: Create a Docker Registry service endpoint
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "docker-hub"
    description: "Docker Hub Registry"
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

- name: Delete a service endpoint
  basicPr0grammer.azure_devops.azure_devops_service_endpoint:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "old-endpoint"
    state: absent
'''

RETURN = r'''
service_endpoint:
  description: Details of the service endpoint
  returned: when state is present
  type: dict
  sample:
    id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    name: "my-api-endpoint"
    type: "generic"
    url: "https://api.example.com"
    description: "Connection to external API"
    is_ready: true
    is_shared: false
changed:
  description: Whether the service endpoint was changed
  returned: always
  type: bool
msg:
  description: Message describing the action taken
  returned: always
  type: str
  sample: "Service endpoint 'my-api-endpoint' created successfully"
'''

import os
import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

AZURE_DEVOPS_IMP_ERR = None
try:
    from azure.devops.connection import Connection
    from azure.devops.v7_1.service_endpoint.models import (
        ServiceEndpoint,
        ServiceEndpointProjectReference,
        EndpointAuthorization,
        ProjectReference
    )
    from msrest.authentication import BasicAuthentication
    HAS_AZURE_DEVOPS = True
except ImportError:
    HAS_AZURE_DEVOPS = False
    AZURE_DEVOPS_IMP_ERR = traceback.format_exc()


def get_credentials(module):
    """Get authentication credentials"""
    pat = module.params.get('personal_access_token') or os.environ.get('AZURE_DEVOPS_PAT')
    if not pat:
        module.fail_json(msg="personal_access_token is required either as parameter or AZURE_DEVOPS_PAT environment variable")
    return BasicAuthentication('', pat)


def connect_to_azure_devops(module, organization):
    """Establish connection to Azure DevOps and get project ID"""
    try:
        credentials = get_credentials(module)
        organization_url = f'https://dev.azure.com/{organization}'
        connection = Connection(base_url=organization_url, creds=credentials)
        client = connection.clients.get_service_endpoint_client()
        
        # Get project ID
        core_client = connection.clients.get_core_client()
        project = core_client.get_project(module.params['project'])
        project_id = project.id
        
        return client, project_id
    except Exception as e:
        module.fail_json(msg=f"Failed to connect to Azure DevOps: {str(e)}")


def get_service_endpoint(module, client, project):
    """Get service endpoint by name"""
    try:
        endpoints = client.get_service_endpoints(project=project)
        for endpoint in endpoints:
            if endpoint.name == module.params['name']:
                return endpoint
        return None
    except Exception as e:
        module.fail_json(msg=f"Failed to get service endpoint: {str(e)}")


def create_service_endpoint(module, client, project_id, name, endpoint_type, url, description, authorization, data):
    """Create a new service endpoint"""
    try:
        auth = EndpointAuthorization(
            scheme=authorization.get('scheme', 'None'),
            parameters=authorization.get('parameters', {})
        )
        
        project_ref = ProjectReference(
            id=project_id,
            name=module.params['project']
        )
        
        se_project_ref = ServiceEndpointProjectReference(
            project_reference=project_ref,
            name=name,
            description=description
        )
        
        endpoint = ServiceEndpoint(
            name=name,
            type=endpoint_type,
            url=url,
            description=description,
            authorization=auth,
            data=data,
            service_endpoint_project_references=[se_project_ref]
        )
        
        result = client.create_service_endpoint(endpoint)
        return True, result
    except Exception as e:
        module.fail_json(msg=f"Failed to create service endpoint: {str(e)}")


def update_service_endpoint(module, client, existing_endpoint, endpoint_type, url, description, authorization, data):
    """Update an existing service endpoint with idempotency checks"""
    try:
        changed = False
        
        if description != existing_endpoint.description:
            existing_endpoint.description = description
            if existing_endpoint.service_endpoint_project_references:
                for ref in existing_endpoint.service_endpoint_project_references:
                    ref.description = description
            changed = True
        
        if url and url != existing_endpoint.url:
            existing_endpoint.url = url
            changed = True
        
        if endpoint_type != existing_endpoint.type:
            existing_endpoint.type = endpoint_type
            changed = True
        
        # Check authorization parameters
        if authorization:
            new_scheme = authorization.get('scheme')
            new_params = authorization.get('parameters', {})
            
            if new_scheme and new_scheme != existing_endpoint.authorization.scheme:
                changed = True
            
            existing_params = existing_endpoint.authorization.parameters or {}
            
            # Known secret parameter keys that Azure doesn't return
            secret_keys = {'password', 'accessToken', 'serviceprincipalkey', 'token', 'apitoken'}
            
            # Only check non-secret parameters for changes
            for key, value in new_params.items():
                if key.lower() not in secret_keys:
                    if key not in existing_params or existing_params.get(key) != value:
                        changed = True
                        break
            
            if changed and new_scheme:
                existing_endpoint.authorization = EndpointAuthorization(
                    scheme=new_scheme or existing_endpoint.authorization.scheme,
                    parameters={**existing_params, **new_params}
                )
        
        # Check data
        if data:
            existing_data = existing_endpoint.data or {}
            for key, value in data.items():
                if key not in existing_data or existing_data.get(key) != value:
                    changed = True
                    existing_endpoint.data = {**existing_data, **data}
                    break
        
        if changed:
            result = client.update_service_endpoint(existing_endpoint, existing_endpoint.id)
            return True, result
        
        return False, existing_endpoint
    except Exception as e:
        module.fail_json(msg=f"Failed to update service endpoint: {str(e)}")


def delete_service_endpoint(module, client, endpoint_id, project_id):
    """Delete a service endpoint"""
    try:
        client.delete_service_endpoint(endpoint_id, [project_id])
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete service endpoint: {str(e)}")


def format_service_endpoint(endpoint):
    """Format service endpoint for return value"""
    if not endpoint:
        return None
    
    return {
        'id': endpoint.id,
        'name': endpoint.name,
        'type': endpoint.type,
        'url': endpoint.url,
        'description': endpoint.description,
        'is_ready': endpoint.is_ready,
        'is_shared': endpoint.is_shared,
        'owner': endpoint.owner
    }


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization=dict(type='str', required=True),
            project=dict(type='str', required=True),
            personal_access_token=dict(type='str', required=False, no_log=True),
            name=dict(type='str', required=True),
            description=dict(type='str', required=False, default=''),
            endpoint_type=dict(
                type='str',
                required=False,
                default='generic',
                choices=['azurerm', 'github', 'dockerregistry', 'generic', 'kubernetes']
            ),
            url=dict(type='str', required=False, default=''),
            authorization=dict(type='dict', required=False, default={}),
            data=dict(type='dict', required=False, default={}),
            state=dict(type='str', default='present', choices=['present', 'absent']),
        ),
        supports_check_mode=True,
    )

    if not HAS_AZURE_DEVOPS:
        module.fail_json(
            msg=missing_required_lib('azure-devops'),
            exception=AZURE_DEVOPS_IMP_ERR
        )

    organization = module.params['organization']
    project = module.params['project']
    name = module.params['name']
    description = module.params.get('description', '')
    endpoint_type = module.params.get('endpoint_type', 'generic')
    url = module.params.get('url', '')
    authorization = module.params.get('authorization', {})
    data = module.params.get('data', {})
    state = module.params['state']

    client, project_id = connect_to_azure_devops(module, organization)
    existing_endpoint = get_service_endpoint(module, client, project)
    
    if state == 'absent':
        if existing_endpoint:
            if not module.check_mode:
                delete_service_endpoint(module, client, existing_endpoint.id, project_id)
            module.exit_json(
                changed=True,
                msg=f"Service endpoint '{name}' deleted successfully",
                service_endpoint=None
            )
        else:
            module.exit_json(
                changed=False,
                msg=f"Service endpoint '{name}' does not exist",
                service_endpoint=None
            )
    
    # state == 'present'
    if existing_endpoint:
        if not module.check_mode:
            changed, updated_endpoint = update_service_endpoint(
                module, client, existing_endpoint, endpoint_type, url, description, authorization, data
            )
        else:
            changed = (
                description != existing_endpoint.description or
                (url and url != existing_endpoint.url) or
                endpoint_type != existing_endpoint.type
            )
            updated_endpoint = existing_endpoint
        
        module.exit_json(
            changed=changed,
            msg=f"Service endpoint '{name}' {'would be updated' if module.check_mode and changed else 'updated' if changed else 'unchanged'}",
            service_endpoint=format_service_endpoint(updated_endpoint)
        )
    else:
        if not module.check_mode:
            changed, new_endpoint = create_service_endpoint(
                module, client, project_id, name, endpoint_type, url, description, authorization, data
            )
        else:
            changed = True
            new_endpoint = None
        
        module.exit_json(
            changed=changed,
            msg=f"Service endpoint '{name}' {'would be created' if module.check_mode else 'created successfully'}",
            service_endpoint=format_service_endpoint(new_endpoint) if new_endpoint else None
        )


if __name__ == '__main__':
    main()
