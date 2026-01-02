#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, basicPr0grammer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_work_item
short_description: Manage Azure DevOps work items
description:
  - Create, update, or delete work items in Azure DevOps
  - Supports all work item types (User Story, Bug, Task, Feature, Epic, etc.)
  - Manage work item fields, tags, and links
version_added: "1.2.0"
options:
  organization_url:
    description:
      - The URL of the Azure DevOps organization
    required: true
    type: str
  personal_access_token:
    description:
      - Personal Access Token (PAT) for authentication
      - If not provided, will use AZURE_DEVOPS_PAT environment variable
    required: false
    type: str
  project:
    description:
      - Name or ID of the project
    required: true
    type: str
  work_item_id:
    description:
      - ID of the work item to update or delete
      - Required when state is absent or when updating existing work item
    required: false
    type: int
  work_item_type:
    description:
      - Type of work item to create
      - Common types include User Story, Bug, Task, Feature, Epic, Issue
    required: false
    type: str
  title:
    description:
      - Title of the work item
    required: false
    type: str
  description:
    description:
      - Description/details of the work item
      - Supports HTML formatting
    required: false
    type: str
  state:
    description:
      - State of the work item
    type: str
    choices: ['present', 'absent']
    default: present
  work_item_state:
    description:
      - Work item state (New, Active, Resolved, Closed, etc.)
      - Available states depend on work item type and process template
    type: str
  assigned_to:
    description:
      - Email or display name of person to assign work item to
    type: str
  area_path:
    description:
      - Area path for the work item
    type: str
  iteration_path:
    description:
      - Iteration path for the work item
    type: str
  tags:
    description:
      - List of tags to add to the work item
    type: list
    elements: str
  priority:
    description:
      - Priority of the work item (1-4, where 1 is highest)
    type: int
  severity:
    description:
      - Severity for bugs (1-4, where 1 is most severe)
    type: str
  acceptance_criteria:
    description:
      - Acceptance criteria for the work item
    type: str
  fields:
    description:
      - Dictionary of additional fields to set
      - Use field reference names (e.g., System.Title, Microsoft.VSTS.Common.Priority)
    type: dict
  parent_work_item_id:
    description:
      - ID of parent work item to link to
    type: int
author:
  - basicPr0grammer
'''

EXAMPLES = r'''
- name: Create a user story
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    work_item_type: "User Story"
    title: "As a user, I want to login"
    description: "Implement user authentication"
    state: present
    work_item_state: "New"
    assigned_to: "user@example.com"
    priority: 1
    tags:
      - authentication
      - sprint-1

- name: Create a bug
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    work_item_type: "Bug"
    title: "Application crashes on login"
    description: "<p>Steps to reproduce:</p><ol><li>Open app</li><li>Enter credentials</li><li>Click login</li></ol>"
    severity: "1 - Critical"
    priority: 1
    state: present

- name: Create a task under a user story
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    work_item_type: "Task"
    title: "Write unit tests for login"
    parent_work_item_id: 123
    state: present

- name: Update work item state
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    work_item_id: 456
    work_item_state: "Resolved"
    state: present

- name: Update work item with custom fields
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    work_item_id: 789
    fields:
      System.Title: "Updated title"
      Microsoft.VSTS.Common.Priority: 2
      Custom.Field: "Custom value"
    state: present

- name: Add tags to existing work item
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    work_item_id: 101
    tags:
      - hotfix
      - production
    state: present

- name: Delete a work item
  basicPr0grammer.azure_devops.azure_devops_work_item:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    work_item_id: 999
    state: absent
'''

RETURN = r'''
work_item:
  description: Information about the work item
  returned: always (except on delete)
  type: dict
  contains:
    id:
      description: Work item ID
      type: int
    type:
      description: Work item type
      type: str
    title:
      description: Work item title
      type: str
    state:
      description: Work item state
      type: str
    url:
      description: Work item URL
      type: str
    fields:
      description: All work item fields
      type: dict
'''

from ansible.module_utils.basic import AnsibleModule
import os


def get_credentials(module):
    """Get authentication credentials"""
    from msrest.authentication import BasicAuthentication
    
    pat = module.params.get('personal_access_token')
    if not pat:
        pat = os.environ.get('AZURE_DEVOPS_PAT')
    
    if not pat:
        module.fail_json(msg="Personal Access Token is required. Provide via personal_access_token parameter or AZURE_DEVOPS_PAT environment variable")
    
    return BasicAuthentication('', pat)


def work_item_to_dict(work_item):
    """Convert work item object to dictionary"""
    if not work_item:
        return None
    
    fields = work_item.fields if hasattr(work_item, 'fields') else {}
    
    return {
        'id': work_item.id,
        'rev': work_item.rev if hasattr(work_item, 'rev') else None,
        'type': fields.get('System.WorkItemType'),
        'title': fields.get('System.Title'),
        'state': fields.get('System.State'),
        'assigned_to': fields.get('System.AssignedTo'),
        'created_date': fields.get('System.CreatedDate'),
        'changed_date': fields.get('System.ChangedDate'),
        'url': work_item.url if hasattr(work_item, 'url') else None,
        'fields': fields
    }


def build_patch_document(module, is_new=True):
    """Build JSON patch document for work item operations"""
    from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation
    
    patch_document = []
    
    # Title
    if module.params.get('title'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/System.Title',
            value=module.params['title']
        ))
    
    # Description
    if module.params.get('description') is not None:
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/System.Description',
            value=module.params['description']
        ))
    
    # Work item state
    if module.params.get('work_item_state'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/System.State',
            value=module.params['work_item_state']
        ))
    
    # Assigned to
    if module.params.get('assigned_to'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/System.AssignedTo',
            value=module.params['assigned_to']
        ))
    
    # Area path
    if module.params.get('area_path'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/System.AreaPath',
            value=module.params['area_path']
        ))
    
    # Iteration path
    if module.params.get('iteration_path'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/System.IterationPath',
            value=module.params['iteration_path']
        ))
    
    # Tags
    if module.params.get('tags'):
        tags_str = '; '.join(module.params['tags'])
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/System.Tags',
            value=tags_str
        ))
    
    # Priority
    if module.params.get('priority') is not None:
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/Microsoft.VSTS.Common.Priority',
            value=module.params['priority']
        ))
    
    # Severity (for bugs)
    if module.params.get('severity'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/Microsoft.VSTS.Common.Severity',
            value=module.params['severity']
        ))
    
    # Acceptance criteria
    if module.params.get('acceptance_criteria'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/fields/Microsoft.VSTS.Common.AcceptanceCriteria',
            value=module.params['acceptance_criteria']
        ))
    
    # Custom fields
    if module.params.get('fields'):
        for field_name, field_value in module.params['fields'].items():
            patch_document.append(JsonPatchOperation(
                op='add',
                path=f'/fields/{field_name}',
                value=field_value
            ))
    
    # Parent link (only for new work items)
    if is_new and module.params.get('parent_work_item_id'):
        patch_document.append(JsonPatchOperation(
            op='add',
            path='/relations/-',
            value={
                'rel': 'System.LinkTypes.Hierarchy-Reverse',
                'url': f"{module.params['organization_url']}/{module.params['project']}/_apis/wit/workItems/{module.params['parent_work_item_id']}"
            }
        ))
    
    return patch_document


def create_work_item(module, wit_client, project, work_item_type):
    """Create a new work item"""
    try:
        patch_document = build_patch_document(module, is_new=True)
        
        if not patch_document:
            module.fail_json(msg="At least one field must be provided to create a work item")
        
        if not module.check_mode:
            work_item = wit_client.create_work_item(
                document=patch_document,
                project=project,
                type=work_item_type
            )
            return work_item, True
        else:
            return None, True
            
    except Exception as e:
        module.fail_json(msg=f"Failed to create work item: {str(e)}")


def update_work_item(module, wit_client, work_item_id, existing_work_item):
    """Update an existing work item"""
    try:
        patch_document = build_patch_document(module, is_new=False)
        
        if not patch_document:
            # No changes needed
            return existing_work_item, False
        
        # Check if update is actually needed
        needs_update = False
        for operation in patch_document:
            field_path = operation.path.replace('/fields/', '')
            current_value = existing_work_item.fields.get(field_path)
            
            if operation.value != current_value:
                needs_update = True
                break
        
        if not needs_update:
            return existing_work_item, False
        
        if not module.check_mode:
            work_item = wit_client.update_work_item(
                document=patch_document,
                id=work_item_id
            )
            return work_item, True
        else:
            return existing_work_item, True
            
    except Exception as e:
        module.fail_json(msg=f"Failed to update work item: {str(e)}")


def delete_work_item(module, wit_client, work_item_id):
    """Delete a work item"""
    try:
        if not module.check_mode:
            wit_client.delete_work_item(
                id=work_item_id,
                destroy=False  # Soft delete - can be restored
            )
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete work item: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type='str', required=True),
            personal_access_token=dict(type='str', required=False, no_log=True),
            project=dict(type='str', required=True),
            work_item_id=dict(type='int', required=False),
            work_item_type=dict(type='str', required=False),
            title=dict(type='str', required=False),
            description=dict(type='str', required=False),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            work_item_state=dict(type='str', required=False),
            assigned_to=dict(type='str', required=False),
            area_path=dict(type='str', required=False),
            iteration_path=dict(type='str', required=False),
            tags=dict(type='list', elements='str', required=False),
            priority=dict(type='int', required=False),
            severity=dict(type='str', required=False),
            acceptance_criteria=dict(type='str', required=False),
            fields=dict(type='dict', required=False),
            parent_work_item_id=dict(type='int', required=False),
        ),
        supports_check_mode=True,
        required_if=[
            ('state', 'absent', ['work_item_id']),
        ]
    )

    try:
        from azure.devops.connection import Connection
    except ImportError:
        module.fail_json(msg="azure-devops package is required. Install it using: pip install azure-devops")

    organization_url = module.params['organization_url']
    project = module.params['project']
    work_item_id = module.params['work_item_id']
    work_item_type = module.params['work_item_type']
    state = module.params['state']

    # Authenticate
    credentials = get_credentials(module)
    connection = Connection(base_url=organization_url, creds=credentials)
    wit_client = connection.clients.get_work_item_tracking_client()

    result = {
        'changed': False,
        'work_item': None
    }

    try:
        # Get existing work item if ID provided
        existing_work_item = None
        if work_item_id:
            try:
                existing_work_item = wit_client.get_work_item(id=work_item_id)
            except Exception:
                if state == 'present':
                    module.fail_json(msg=f"Work item {work_item_id} not found")
                # For absent state, if work item doesn't exist, that's OK
        
        if state == 'present':
            if work_item_id and existing_work_item:
                # Update existing work item
                work_item, changed = update_work_item(module, wit_client, work_item_id, existing_work_item)
                result['changed'] = changed
                if work_item:
                    result['work_item'] = work_item_to_dict(work_item)
            else:
                # Create new work item
                if not work_item_type:
                    module.fail_json(msg="work_item_type is required when creating a new work item")
                if not module.params.get('title'):
                    module.fail_json(msg="title is required when creating a new work item")
                
                work_item, changed = create_work_item(module, wit_client, project, work_item_type)
                result['changed'] = changed
                if work_item:
                    result['work_item'] = work_item_to_dict(work_item)
                elif module.check_mode:
                    result['work_item'] = {'state': 'would_be_created'}
        
        elif state == 'absent':
            if existing_work_item:
                changed = delete_work_item(module, wit_client, work_item_id)
                result['changed'] = changed
                result['work_item'] = {'state': 'deleted', 'id': work_item_id}
            else:
                result['work_item'] = {'state': 'already_absent'}

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"An error occurred: {str(e)}")


if __name__ == '__main__':
    main()
