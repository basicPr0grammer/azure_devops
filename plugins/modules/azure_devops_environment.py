#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, basicPr0grammer
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_environment
short_description: Manage Azure DevOps environments
description:
    - Create, update, or delete Azure DevOps environments
    - Manage environment approvers and checks
    - Grant pipeline permissions to environments
    - Fully idempotent operations
version_added: "1.2.0"
author:
    - basicPr0grammer
options:
    organization_url:
        description:
            - The URL of the Azure DevOps organization
        required: true
        type: str
    
    project:
        description:
            - Name or ID of the project
        required: true
        type: str
    
    name:
        description:
            - Name of the environment
        required: true
        type: str
    
    description:
        description:
            - Description of the environment
        required: false
        type: str
    
    state:
        description:
            - State of the environment
        choices: ['present', 'absent']
        default: 'present'
        type: str
    
    approvers:
        description:
            - List of user IDs or email addresses who can approve deployments
            - When specified, creates/updates an approval check on the environment
        required: false
        type: list
        elements: str
    
    min_approvers:
        description:
            - Minimum number of approvers required
            - Only applicable when approvers are specified
        required: false
        type: int
        default: 1
    
    approval_instructions:
        description:
            - Instructions for approvers
        required: false
        type: str
    
    approval_timeout:
        description:
            - Timeout in minutes for approvals (default 30 days = 43200 minutes)
        required: false
        type: int
        default: 43200
    
    pipeline_permissions:
        description:
            - List of pipeline IDs or names to grant access to this environment
            - When specified, grants the pipelines permission to use the environment
        required: false
        type: list
        elements: raw
    
notes:
    - Requires AZURE_DEVOPS_PAT environment variable with appropriate permissions
    - PAT needs Environment (Read, Write & Manage), Pipelines (Read & Execute) scopes
    - Use organization_url format like https://dev.azure.com/yourorg
'''

EXAMPLES = r'''
- name: Create a simple environment
  basicPr0grammer.azure_devops.azure_devops_environment:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "production"
    description: "Production environment"
    state: present

- name: Create environment with approvers
  basicPr0grammer.azure_devops.azure_devops_environment:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "production"
    description: "Production environment"
    approvers:
      - "user1@example.com"
      - "user2@example.com"
    min_approvers: 2
    approval_instructions: "Please review before deploying to production"
    approval_timeout: 1440  # 24 hours
    state: present

- name: Grant pipeline access to environment
  basicPr0grammer.azure_devops.azure_devops_environment:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "staging"
    pipeline_permissions:
      - "CI/CD Pipeline"
      - 12345  # Pipeline ID
    state: present

- name: Complete environment setup with all features
  basicPr0grammer.azure_devops.azure_devops_environment:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "production"
    description: "Production deployment environment"
    approvers:
      - "admin@example.com"
      - "manager@example.com"
    min_approvers: 1
    approval_instructions: "Ensure all tests pass before approval"
    pipeline_permissions:
      - "Production Deploy Pipeline"
    state: present

- name: Remove environment
  basicPr0grammer.azure_devops.azure_devops_environment:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "old-staging"
    state: absent

- name: Use PAT from environment variable
  basicPr0grammer.azure_devops.azure_devops_environment:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "development"
    state: present
  environment:
    AZURE_DEVOPS_PAT: "{{ lookup('env', 'AZURE_DEVOPS_PAT') }}"
'''

RETURN = r'''
environment:
    description: Details of the environment
    returned: always
    type: dict
    sample:
        id: 1850
        name: "production"
        description: "Production environment"
        project_id: "8c738f12-50f8-479e-a69b-151cc89c5590"
        created_on: "2026-01-01T10:00:00Z"
changed:
    description: Whether the environment was changed
    returned: always
    type: bool
approvers_configured:
    description: Whether approvers were configured
    returned: when approvers are specified
    type: bool
pipeline_permissions_granted:
    description: List of pipelines granted access
    returned: when pipeline_permissions are specified
    type: list
'''

import os
import json
import base64
import requests
from ansible.module_utils.basic import AnsibleModule


def get_auth_header(pat):
    """Create authentication header from PAT"""
    token = base64.b64encode(f':{pat}'.encode()).decode()
    return {'Authorization': f'Basic {token}'}


def get_project_id(session, org_url, project_name):
    """Get project ID from project name"""
    url = f"{org_url}/_apis/projects/{project_name}?api-version=7.0"
    response = session.get(url)
    if response.status_code == 200:
        return response.json()['id']
    return None


def get_environment(session, org_url, project, env_name):
    """Get environment by name"""
    url = f"{org_url}/{project}/_apis/distributedtask/environments?api-version=7.0"
    response = session.get(url)
    
    if response.status_code != 200:
        return None
    
    environments = response.json().get('value', [])
    for env in environments:
        if env['name'] == env_name:
            return env
    
    return None


def create_environment(session, org_url, project, name, description=None):
    """Create a new environment"""
    url = f"{org_url}/{project}/_apis/distributedtask/environments?api-version=7.0"
    
    payload = {
        'name': name
    }
    
    if description:
        payload['description'] = description
    
    response = session.post(url, json=payload)
    
    if response.status_code in [200, 201]:
        return response.json()
    
    return None


def update_environment(session, org_url, project, env_id, name=None, description=None):
    """Update an existing environment"""
    url = f"{org_url}/{project}/_apis/distributedtask/environments/{env_id}?api-version=7.0"
    
    payload = {}
    
    if name:
        payload['name'] = name
    if description is not None:
        payload['description'] = description
    
    response = session.patch(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    
    return None


def delete_environment(session, org_url, project, env_id):
    """Delete an environment"""
    url = f"{org_url}/{project}/_apis/distributedtask/environments/{env_id}?api-version=7.0"
    response = session.delete(url)
    return response.status_code == 204


def get_user_id(session, org_url, email_or_id):
    """Get user descriptor/ID from email or direct ID"""
    # If it's already a UUID format, return it
    if '-' in email_or_id and len(email_or_id) == 36:
        return email_or_id
    
    # Search for user by email
    url = f"{org_url}/_apis/identities?searchFilter=General&filterValue={email_or_id}&api-version=7.0"
    response = session.get(url)
    
    if response.status_code == 200:
        identities = response.json().get('value', [])
        if identities:
            return identities[0]['id']
    
    # Try Graph API
    url = f"{org_url}/_apis/graph/users?api-version=7.0-preview.1"
    response = session.get(url)
    
    if response.status_code == 200:
        users = response.json().get('value', [])
        for user in users:
            if user.get('mailAddress', '').lower() == email_or_id.lower():
                return user['descriptor']
    
    return None


def get_environment_checks(session, org_url, project, env_id):
    """Get all checks configured on an environment"""
    url = f"{org_url}/{project}/_apis/pipelines/checks/configurations?resourceType=environment&resourceId={env_id}&api-version=7.1-preview.1"
    response = session.get(url)
    
    if response.status_code == 200:
        return response.json().get('value', [])
    
    return []


def get_approval_check(session, org_url, project, env_id):
    """Get the approval check if it exists"""
    checks = get_environment_checks(session, org_url, project, env_id)
    
    for check in checks:
        if check.get('type', {}).get('name') == 'Approval':
            return check
    
    return None


def create_approval_check(session, org_url, project, env_id, approvers, min_approvers=1, 
                         instructions=None, timeout=43200):
    """Create an approval check on the environment"""
    url = f"{org_url}/{project}/_apis/pipelines/checks/configurations?api-version=7.1-preview.1"
    
    # Build approvers list
    approver_list = []
    for approver in approvers:
        user_id = get_user_id(session, org_url, approver)
        if user_id:
            approver_list.append({'id': user_id})
    
    if not approver_list:
        return None
    
    payload = {
        'type': {
            'name': 'Approval'
        },
        'settings': {
            'approvers': approver_list,
            'minRequiredApprovers': min_approvers,
            'instructions': instructions or '',
            'executionOrder': 1,
            'blockedApprovers': [],
            'requesterCannotBeApprover': False
        },
        'resource': {
            'type': 'environment',
            'id': str(env_id)
        },
        'timeout': timeout
    }
    
    response = session.post(url, json=payload)
    
    if response.status_code in [200, 201]:
        return response.json()
    
    return None


def update_approval_check(session, org_url, project, check_id, approvers, min_approvers=1,
                         instructions=None, timeout=43200):
    """Update an existing approval check"""
    url = f"{org_url}/{project}/_apis/pipelines/checks/configurations/{check_id}?api-version=7.1-preview.1"
    
    # Build approvers list
    approver_list = []
    for approver in approvers:
        user_id = get_user_id(session, org_url, approver)
        if user_id:
            approver_list.append({'id': user_id})
    
    if not approver_list:
        return None
    
    # Get existing check to preserve fields
    get_url = f"{org_url}/{project}/_apis/pipelines/checks/configurations/{check_id}?api-version=7.1-preview.1"
    get_response = session.get(get_url)
    
    if get_response.status_code != 200:
        return None
    
    existing_check = get_response.json()
    
    payload = {
        'type': existing_check['type'],
        'settings': {
            'approvers': approver_list,
            'minRequiredApprovers': min_approvers,
            'instructions': instructions or '',
            'executionOrder': 1,
            'blockedApprovers': [],
            'requesterCannotBeApprover': False
        },
        'resource': existing_check['resource'],
        'timeout': timeout
    }
    
    response = session.put(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    
    return None


def get_pipeline_by_name_or_id(session, org_url, project, pipeline_name_or_id):
    """Get pipeline by name or ID"""
    # Try as ID first
    try:
        pipeline_id = int(pipeline_name_or_id)
        url = f"{org_url}/{project}/_apis/pipelines/{pipeline_id}?api-version=7.0"
        response = session.get(url)
        if response.status_code == 200:
            return response.json()
    except (ValueError, TypeError):
        pass
    
    # Search by name
    url = f"{org_url}/{project}/_apis/pipelines?api-version=7.0"
    response = session.get(url)
    
    if response.status_code == 200:
        pipelines = response.json().get('value', [])
        for pipeline in pipelines:
            if pipeline['name'] == pipeline_name_or_id:
                return pipeline
    
    return None


def grant_pipeline_permission(session, org_url, project, project_id, env_id, pipeline_id):
    """Grant a pipeline permission to access an environment"""
    url = f"{org_url}/{project}/_apis/pipelines/pipelinePermissions/environment/{env_id}?api-version=7.1-preview.1"
    
    payload = {
        'pipelines': [{
            'id': pipeline_id,
            'authorized': True
        }]
    }
    
    response = session.patch(url, json=payload)
    
    return response.status_code == 200


def get_pipeline_permissions(session, org_url, project, env_id):
    """Get all pipeline permissions for an environment"""
    url = f"{org_url}/{project}/_apis/pipelines/pipelinePermissions/environment/{env_id}?api-version=7.1-preview.1"
    response = session.get(url)
    
    if response.status_code == 200:
        return response.json().get('pipelines', [])
    
    return []


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type='str', required=True),
            project=dict(type='str', required=True),
            name=dict(type='str', required=True),
            description=dict(type='str', required=False),
            state=dict(type='str', choices=['present', 'absent'], default='present'),
            approvers=dict(type='list', elements='str', required=False),
            min_approvers=dict(type='int', default=1),
            approval_instructions=dict(type='str', required=False),
            approval_timeout=dict(type='int', default=43200),
            pipeline_permissions=dict(type='list', elements='raw', required=False),
        ),
        supports_check_mode=True
    )
    
    # Get PAT from environment
    pat = os.environ.get('AZURE_DEVOPS_PAT')
    if not pat:
        module.fail_json(msg='AZURE_DEVOPS_PAT environment variable must be set')
    
    org_url = module.params['organization_url'].rstrip('/')
    project = module.params['project']
    name = module.params['name']
    description = module.params.get('description')
    state = module.params['state']
    approvers = module.params.get('approvers')
    min_approvers = module.params['min_approvers']
    approval_instructions = module.params.get('approval_instructions')
    approval_timeout = module.params['approval_timeout']
    pipeline_permissions = module.params.get('pipeline_permissions')
    
    # Create session
    session = requests.Session()
    session.headers.update(get_auth_header(pat))
    session.headers.update({'Content-Type': 'application/json'})
    
    result = {
        'changed': False,
        'environment': {}
    }
    
    try:
        # Get project ID (needed for some operations)
        project_id = get_project_id(session, org_url, project)
        if not project_id:
            module.fail_json(msg=f"Project '{project}' not found")
        
        # Check if environment exists
        existing_env = get_environment(session, org_url, project, name)
        
        if state == 'absent':
            if existing_env:
                if not module.check_mode:
                    if delete_environment(session, org_url, project, existing_env['id']):
                        result['changed'] = True
                        result['environment'] = {'name': name, 'state': 'deleted'}
                    else:
                        module.fail_json(msg=f"Failed to delete environment '{name}'")
                else:
                    result['changed'] = True
                    result['environment'] = {'name': name, 'state': 'would_be_deleted'}
            # If doesn't exist, no change needed
            
        else:  # state == 'present'
            if not existing_env:
                # Create new environment
                if not module.check_mode:
                    env = create_environment(session, org_url, project, name, description)
                    if not env:
                        module.fail_json(msg=f"Failed to create environment '{name}'")
                    result['environment'] = env
                    result['changed'] = True
                    env_id = env['id']
                else:
                    result['changed'] = True
                    result['environment'] = {'name': name, 'state': 'would_be_created'}
                    module.exit_json(**result)
            else:
                # Update existing environment if description changed
                env_id = existing_env['id']
                result['environment'] = existing_env
                
                if description and existing_env.get('description') != description:
                    if not module.check_mode:
                        env = update_environment(session, org_url, project, env_id, description=description)
                        if env:
                            result['environment'] = env
                            result['changed'] = True
                    else:
                        result['changed'] = True
            
            # Configure approvers if specified
            if approvers and not module.check_mode:
                existing_approval = get_approval_check(session, org_url, project, env_id)
                
                if existing_approval:
                    # Update existing approval check
                    updated = update_approval_check(
                        session, org_url, project, existing_approval['id'],
                        approvers, min_approvers, approval_instructions, approval_timeout
                    )
                    if updated:
                        result['approvers_configured'] = True
                        result['changed'] = True
                else:
                    # Create new approval check
                    created = create_approval_check(
                        session, org_url, project, env_id,
                        approvers, min_approvers, approval_instructions, approval_timeout
                    )
                    if created:
                        result['approvers_configured'] = True
                        result['changed'] = True
            
            # Grant pipeline permissions if specified
            if pipeline_permissions and not module.check_mode:
                granted_pipelines = []
                existing_permissions = get_pipeline_permissions(session, org_url, project, env_id)
                existing_pipeline_ids = {p['id'] for p in existing_permissions if p.get('authorized')}
                
                for pipeline_ref in pipeline_permissions:
                    pipeline = get_pipeline_by_name_or_id(session, org_url, project, pipeline_ref)
                    if pipeline:
                        pipeline_id = pipeline['id']
                        
                        # Only grant if not already granted
                        if pipeline_id not in existing_pipeline_ids:
                            if grant_pipeline_permission(session, org_url, project, project_id, env_id, pipeline_id):
                                granted_pipelines.append(pipeline['name'])
                                result['changed'] = True
                        else:
                            granted_pipelines.append(f"{pipeline['name']} (already granted)")
                
                if granted_pipelines:
                    result['pipeline_permissions_granted'] = granted_pipelines
        
        module.exit_json(**result)
        
    except requests.exceptions.RequestException as e:
        module.fail_json(msg=f"API request failed: {str(e)}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == '__main__':
    main()
