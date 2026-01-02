#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, basicPr0grammer
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_pipeline_approval
short_description: Manage Azure DevOps YAML pipeline approvals
description:
    - Approve or reject pending approvals for YAML pipelines
    - Query approval status for pipeline runs
    - Supports environment approvals and checks
version_added: "1.1.0"
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
    
    build_id:
        description:
            - The ID of the build/run that requires approval
            - Required when state is 'approve' or 'reject'
        required: false
        type: int
    
    approval_id:
        description:
            - Specific approval ID to approve/reject
            - If not provided, all pending approvals for the build will be processed
        required: false
        type: str
    
    state:
        description:
            - The desired state of the approval
            - 'query' to get pending approvals
            - 'approve' to approve pending approvals
            - 'reject' to reject pending approvals
        required: true
        type: str
        choices: ['query', 'approve', 'reject']
    
    comment:
        description:
            - Optional comment for the approval/rejection
        required: false
        type: str
    
requirements:
    - azure-devops>=7.1.0b4
    
notes:
    - Requires AZURE_DEVOPS_PAT environment variable with appropriate permissions
    - PAT requires 'Build: Read & Execute' and 'Release: Read, write, & execute' scopes
'''

EXAMPLES = r'''
# Query pending approvals for a build
- name: Get pending approvals
  basicPr0grammer.azure_devops.azure_devops_pipeline_approval:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    build_id: 12345
    state: query
  register: approvals

# Approve all pending approvals for a build
- name: Approve pipeline run
  basicPr0grammer.azure_devops.azure_devops_pipeline_approval:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    build_id: 12345
    state: approve
    comment: "Automated approval by Ansible"

# Reject a specific approval
- name: Reject approval
  basicPr0grammer.azure_devops.azure_devops_pipeline_approval:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    build_id: 12345
    approval_id: "abc-123"
    state: reject
    comment: "Failed validation checks"
'''

RETURN = r'''
approvals:
    description: List of approvals found or processed
    returned: always
    type: list
    elements: dict
    sample: [
        {
            "id": "abc-123",
            "status": "pending",
            "approver": "user@example.com"
        }
    ]
    
changed:
    description: Whether any changes were made
    returned: always
    type: bool
'''

import os
import base64
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url

try:
    from msrest.authentication import BasicAuthentication
    from azure.devops.connection import Connection
    from azure.devops.v7_1.build import models as build_models
    HAS_AZURE_DEVOPS = True
except ImportError:
    HAS_AZURE_DEVOPS = False

try:
    import json
    HAS_JSON = True
except ImportError:
    HAS_JSON = False


def get_pending_approvals(module, organization_url, project, pat, build_id=None):
    """Get pending approvals for a project or specific build"""
    
    # Extract organization from URL
    org = organization_url.rstrip('/').split('/')[-1]
    
    # Prepare auth header
    auth_str = base64.b64encode(f":{pat}".encode()).decode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_str}'
    }
    
    # Get all pending approvals for the project
    url = f"https://dev.azure.com/{org}/{project}/_apis/pipelines/approvals"
    params = 'api-version=7.1-preview.1'
    
    try:
        response = open_url(f"{url}?{params}", headers=headers, method='GET')
        data = json.loads(response.read())
        
        approvals = data.get('value', [])
        
        # Filter by build_id if provided
        if build_id:
            approvals = [a for a in approvals if a.get('pipeline', {}).get('owner', {}).get('id') == build_id]
        
        # Filter to only pending approvals
        pending_approvals = [a for a in approvals if a.get('status') == 'pending']
        
        # Format the response
        formatted_approvals = []
        for approval in pending_approvals:
            formatted_approvals.append({
                'id': approval.get('id'),
                'status': approval.get('status'),
                'pipeline_name': approval.get('pipeline', {}).get('name'),
                'pipeline_id': approval.get('pipeline', {}).get('id'),
                'build_id': approval.get('pipeline', {}).get('owner', {}).get('id'),
                'build_name': approval.get('pipeline', {}).get('owner', {}).get('name'),
                'instructions': approval.get('instructions', ''),
                'created_on': approval.get('createdOn'),
                'min_required_approvers': approval.get('minRequiredApprovers', 1)
            })
        
        return formatted_approvals
        
    except Exception as e:
        module.fail_json(msg=f"Failed to get approvals: {str(e)}")


def approve_or_reject_approval(module, organization_url, project, pat, approval_id, action, comment):
    """Approve or reject a pending approval using REST API"""
    
    # Extract organization from URL
    org = organization_url.rstrip('/').split('/')[-1]
    
    # Prepare auth header
    auth_str = base64.b64encode(f":{pat}".encode()).decode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth_str}'
    }
    
    # Prepare approval data
    status = 'approved' if action == 'approve' else 'rejected'
    approval_data = [{
        'approvalId': approval_id,
        'status': status,
        'comment': comment
    }]
    
    # PATCH the approval
    url = f"https://dev.azure.com/{org}/{project}/_apis/pipelines/approvals"
    params = 'api-version=7.1-preview.1'
    
    try:
        response = open_url(
            f"{url}?{params}",
            headers=headers,
            method='PATCH',
            data=json.dumps(approval_data)
        )
        
        result = json.loads(response.read())
        
        # Check if approval was successful
        if result.get('value') and len(result['value']) > 0:
            updated_approval = result['value'][0]
            return True, updated_approval.get('status')
        
        return False, None
        
    except Exception as e:
        module.fail_json(msg=f"Failed to {action} approval: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type='str', required=True),
            project=dict(type='str', required=True),
            build_id=dict(type='int', required=False),
            approval_id=dict(type='str', required=False),
            state=dict(type='str', required=True, choices=['query', 'approve', 'reject']),
            comment=dict(type='str', required=False, default=''),
        ),
        required_if=[
            ('state', 'approve', ['build_id']),
            ('state', 'reject', ['build_id']),
        ],
        supports_check_mode=True
    )

    if not HAS_AZURE_DEVOPS:
        module.fail_json(msg='azure-devops SDK is required for this module')
    
    if not HAS_JSON:
        module.fail_json(msg='json module is required')

    organization_url = module.params['organization_url']
    project = module.params['project']
    build_id = module.params['build_id']
    approval_id = module.params['approval_id']
    state = module.params['state']
    comment = module.params['comment']

    # Get PAT from environment
    pat = os.environ.get('AZURE_DEVOPS_PAT')
    if not pat:
        module.fail_json(msg='AZURE_DEVOPS_PAT environment variable must be set')

    result = {
        'changed': False,
        'approvals': []
    }

    if state == 'query':
        # Get pending approvals
        approvals = get_pending_approvals(module, organization_url, project, pat, build_id)
        result['approvals'] = approvals
        result['count'] = len(approvals)
        
    elif state in ['approve', 'reject']:
        # Get pending approvals first
        approvals = get_pending_approvals(module, organization_url, project, pat, build_id)
        
        if not approvals:
            module.exit_json(**result, msg='No pending approvals found')
        
        # Filter by approval_id if provided
        if approval_id:
            approvals = [a for a in approvals if a['id'] == approval_id]
            if not approvals:
                module.fail_json(msg=f'Approval {approval_id} not found or not pending')
        
        # Process approvals
        action = 'approve' if state == 'approve' else 'reject'
        processed_approvals = []
        
        for approval in approvals:
            if not module.check_mode:
                changed, new_status = approve_or_reject_approval(
                    module, organization_url, project, pat,
                    approval['id'], action, comment
                )
                if changed:
                    result['changed'] = True
                    approval['status'] = new_status
            else:
                result['changed'] = True
            
            processed_approvals.append(approval)
        
        result['approvals'] = processed_approvals

    module.exit_json(**result)


if __name__ == '__main__':
    main()
