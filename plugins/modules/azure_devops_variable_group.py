#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, basicPr0grammer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_variable_group
short_description: Manage Azure DevOps Variable Groups
description:
  - Create, update, or delete Azure DevOps Variable Groups.
  - Manage variables within variable groups including secrets.
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
      - The name of the variable group.
    required: true
    type: str
  description:
    description:
      - Description of the variable group.
    required: false
    type: str
    default: ""
  variables:
    description:
      - Dictionary of variables to set in the variable group.
      - Each variable can have 'value' and 'is_secret' keys.
      - If only a string is provided, it's treated as the value with is_secret=false.
    required: false
    type: dict
    default: {}
  state:
    description:
      - Whether the variable group should exist or not.
    choices: ['present', 'absent']
    default: present
    type: str
requirements:
  - azure-devops>=7.1.0
notes:
  - The PAT must have permissions to read and manage variable groups.
  - When updating secrets, you must provide the new value even if unchanged.
  - Azure DevOps doesn't return secret values, so they're always marked as changed if provided.
'''

EXAMPLES = r'''
- name: Create a variable group with plain text variables
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "my-variable-group"
    description: "Variables for my application"
    variables:
      ENV: "production"
      DEBUG: "false"
      APP_URL: "https://app.example.com"
    state: present

- name: Create a variable group with secrets
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "my-secrets"
    description: "Secret variables"
    variables:
      API_KEY:
        value: "super-secret-key"
        is_secret: true
      DB_PASSWORD:
        value: "{{ db_password }}"
        is_secret: true
      PUBLIC_CONFIG: "not-secret"
    state: present

- name: Update variables in existing group
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "my-variable-group"
    variables:
      ENV: "staging"
      NEW_VAR: "new-value"
    state: present

- name: Delete a variable group
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "myorg"
    project: "myproject"
    personal_access_token: "{{ ado_pat }}"
    name: "my-variable-group"
    state: absent

- name: Use PAT from environment variable
  basicPr0grammer.azure_devops.azure_devops_variable_group:
    organization: "myorg"
    project: "myproject"
    name: "my-variable-group"
    variables:
      KEY: "value"
    state: present
  environment:
    AZURE_DEVOPS_PAT: "{{ ado_pat }}"
'''

RETURN = r'''
variable_group:
  description: Details of the variable group
  returned: when state is present
  type: dict
  sample:
    id: 1
    name: "my-variable-group"
    description: "Variables for my application"
    variables:
      ENV:
        value: "production"
        is_secret: false
      API_KEY:
        value: null
        is_secret: true
changed:
  description: Whether the variable group was changed
  returned: always
  type: bool
msg:
  description: Message describing the action taken
  returned: always
  type: str
  sample: "Variable group 'my-variable-group' created successfully"
'''

import os
import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

AZURE_DEVOPS_IMP_ERR = None
try:
    from azure.devops.connection import Connection
    from azure.devops.v7_1.task_agent.models import (
        VariableGroup,
        VariableGroupParameters,
        VariableGroupProjectReference,
        ProjectReference,
        VariableValue
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
    """Establish connection to Azure DevOps"""
    try:
        credentials = get_credentials(module)
        organization_url = f'https://dev.azure.com/{organization}'
        connection = Connection(base_url=organization_url, creds=credentials)
        return connection.clients.get_task_agent_client()
    except Exception as e:
        module.fail_json(msg=f"Failed to connect to Azure DevOps: {str(e)}")


def normalize_variables(variables):
    """
    Normalize variables to consistent format
    Converts string values to dict format: {'value': str, 'is_secret': bool}
    """
    normalized = {}
    for key, value in variables.items():
        if isinstance(value, dict):
            normalized[key] = {
                'value': value.get('value', ''),
                'is_secret': value.get('is_secret', False)
            }
        else:
            normalized[key] = {
                'value': str(value) if value is not None else '',
                'is_secret': False
            }
    return normalized


def get_variable_group(client, project, name):
    """Get variable group by name"""
    try:
        groups = client.get_variable_groups(project=project, group_name=name)
        if groups:
            return groups[0]
        return None
    except Exception:
        return None


def get_variable_group_by_id(client, project, group_id):
    """Get variable group by ID"""
    try:
        return client.get_variable_group(project=project, group_id=group_id)
    except Exception:
        return None


def create_variable_group(module, client, project, name, description, variables):
    """Create a new variable group"""
    try:
        normalized_vars = normalize_variables(variables)
        
        # Create VariableValue objects
        variable_dict = {}
        for key, var_data in normalized_vars.items():
            variable_dict[key] = VariableValue(
                value=var_data['value'],
                is_secret=var_data['is_secret']
            )
        
        # Create project reference
        project_ref = ProjectReference(name=project)
        
        # Create variable group project reference
        vg_project_ref = VariableGroupProjectReference(
            name=name,
            description=description,
            project_reference=project_ref
        )
        
        # Create variable group parameters
        parameters = VariableGroupParameters(
            name=name,
            description=description,
            variables=variable_dict,
            type="Vsts",
            variable_group_project_references=[vg_project_ref]
        )
        
        result = client.add_variable_group(parameters)
        return True, result
    except Exception as e:
        module.fail_json(msg=f"Failed to create variable group: {str(e)}")


def update_variable_group(module, client, project, existing_group, description, variables):
    """Update an existing variable group with idempotency checks"""
    try:
        changed = False
        update_needed = False
        
        # Check description
        if description != existing_group.description:
            existing_group.description = description
            changed = True
            update_needed = True
        
        normalized_vars = normalize_variables(variables)
        existing_vars = existing_group.variables or {}
        
        # Compare and update variables
        for key, var_data in normalized_vars.items():
            needs_update = False
            
            if key not in existing_vars:
                needs_update = True
            else:
                existing_var = existing_vars[key]
                if var_data['is_secret'] != existing_var.is_secret:
                    needs_update = True
                
                if not var_data['is_secret']:
                    if var_data['value'] != existing_var.value:
                        needs_update = True
                else:
                    # For secrets, Azure doesn't return values so we mark as changed if provided
                    if var_data['value']:
                        needs_update = True
            
            if needs_update:
                existing_vars[key] = VariableValue(
                    value=var_data['value'],
                    is_secret=var_data['is_secret']
                )
                changed = True
                update_needed = True
        
        if update_needed:
            existing_group.variables = existing_vars
            
            project_ref = ProjectReference(name=project)
            vg_project_ref = VariableGroupProjectReference(
                name=existing_group.name,
                description=existing_group.description,
                project_reference=project_ref
            )
            
            parameters = VariableGroupParameters(
                name=existing_group.name,
                description=existing_group.description,
                variables=existing_vars,
                type=existing_group.type,
                variable_group_project_references=[vg_project_ref]
            )
            
            result = client.update_variable_group(parameters, existing_group.id)
            return True, result
        
        return False, existing_group
    except Exception as e:
        module.fail_json(msg=f"Failed to update variable group: {str(e)}")


def delete_variable_group(module, client, group_id, variable_group=None):
    """Delete a variable group"""
    try:
        project_ids = []
        if variable_group and hasattr(variable_group, 'variable_group_project_references'):
            for ref in variable_group.variable_group_project_references or []:
                if ref.project_reference and ref.project_reference.id:
                    project_ids.append(ref.project_reference.id)
        
        if not project_ids:
            fetched_group = get_variable_group_by_id(client, module.params['project'], group_id)
            if fetched_group and hasattr(fetched_group, 'variable_group_project_references'):
                for ref in fetched_group.variable_group_project_references or []:
                    if ref.project_reference and ref.project_reference.id:
                        project_ids.append(ref.project_reference.id)
        
        client.delete_variable_group(group_id, project_ids if project_ids else [])
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete variable group: {str(e)}")


def format_variable_group(group):
    """Format variable group for return value"""
    if not group:
        return None
    
    variables = {}
    if group.variables:
        for key, var in group.variables.items():
            variables[key] = {
                'value': var.value if not var.is_secret else None,
                'is_secret': var.is_secret
            }
    
    return {
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'variables': variables,
        'type': group.type
    }


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization=dict(type='str', required=True),
            project=dict(type='str', required=True),
            personal_access_token=dict(type='str', required=False, no_log=True),
            name=dict(type='str', required=True),
            description=dict(type='str', required=False, default=''),
            variables=dict(type='dict', required=False, default={}),
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
    variables = module.params.get('variables', {})
    state = module.params['state']

    client = connect_to_azure_devops(module, organization)
    existing_group = get_variable_group(client, project, name)
    
    if state == 'absent':
        if existing_group:
            if not module.check_mode:
                delete_variable_group(module, client, existing_group.id, existing_group)
            module.exit_json(
                changed=True,
                msg=f"Variable group '{name}' deleted successfully",
                variable_group=None
            )
        else:
            module.exit_json(
                changed=False,
                msg=f"Variable group '{name}' does not exist",
                variable_group=None
            )
    
    # state == 'present'
    if existing_group:
        if not module.check_mode:
            changed, updated_group = update_variable_group(module, client, project, existing_group, description, variables)
        else:
            normalized_vars = normalize_variables(variables)
            changed = (description != existing_group.description or
                      any(key not in existing_group.variables for key in normalized_vars))
            updated_group = existing_group
        
        module.exit_json(
            changed=changed,
            msg=f"Variable group '{name}' {'would be updated' if module.check_mode and changed else 'updated' if changed else 'unchanged'}",
            variable_group=format_variable_group(updated_group)
        )
    else:
        if not module.check_mode:
            changed, new_group = create_variable_group(module, client, project, name, description, variables)
        else:
            changed = True
            new_group = None
        
        module.exit_json(
            changed=changed,
            msg=f"Variable group '{name}' {'would be created' if module.check_mode else 'created successfully'}",
            variable_group=format_variable_group(new_group) if new_group else None
        )


if __name__ == '__main__':
    main()
