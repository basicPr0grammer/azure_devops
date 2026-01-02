#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, basicPr0grammer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_branch_policy
short_description: Manage Azure DevOps branch policies
description:
  - Create, update, or delete branch policies in Azure DevOps
  - Supports minimum reviewers, work item linking, comment resolution, and build validation policies
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
  repository_id:
    description:
      - ID of the repository to apply the policy to
    required: true
    type: str
  branch_name:
    description:
      - Name of the branch to protect (e.g., 'main', 'develop', 'refs/heads/main')
      - Will be normalized to refs/heads/branch format
    required: true
    type: str
  policy_type:
    description:
      - Type of branch policy to manage
    required: true
    type: str
    choices:
      - minimum_reviewers
      - work_item_linking
      - comment_resolution
      - build_validation
      - required_reviewers
      - merge_strategy
  state:
    description:
      - State of the policy
    type: str
    choices: ['present', 'absent']
    default: present
  is_blocking:
    description:
      - Whether the policy should block completion if not satisfied
      - If false, policy acts as a warning only
    type: bool
    default: true
  is_enabled:
    description:
      - Whether the policy is enabled
    type: bool
    default: true
  minimum_approver_count:
    description:
      - Minimum number of reviewers required (for minimum_reviewers policy)
    type: int
  creator_vote_counts:
    description:
      - Whether the creator's vote counts toward the minimum (for minimum_reviewers policy)
    type: bool
    default: false
  allow_downvotes:
    description:
      - Whether downvotes are allowed (for minimum_reviewers policy)
    type: bool
    default: false
  reset_on_source_push:
    description:
      - Reset reviewer votes when source branch is updated (for minimum_reviewers policy)
    type: bool
    default: true
  build_definition_id:
    description:
      - ID of the build pipeline to run (for build_validation policy)
    type: int
  build_display_name:
    description:
      - Display name for the build policy (for build_validation policy)
    type: str
  build_manual_queue_only:
    description:
      - Whether build must be queued manually (for build_validation policy)
    type: bool
    default: false
  build_queue_on_source_update_only:
    description:
      - Queue build only when source branch is updated (for build_validation policy)
    type: bool
    default: true
  build_valid_duration:
    description:
      - How long the build is valid in minutes (for build_validation policy)
      - 0 means the build is always valid
    type: int
    default: 720
  required_reviewer_ids:
    description:
      - List of reviewer IDs to require (for required_reviewers policy)
    type: list
    elements: str
  path_filters:
    description:
      - File path patterns to trigger required reviewers (for required_reviewers policy)
    type: list
    elements: str
  use_squash_merge:
    description:
      - Require squash merge (for merge_strategy policy)
    type: bool
author:
  - basicPr0grammer
'''

EXAMPLES = r'''
- name: Require 2 reviewers for main branch
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: minimum_reviewers
    state: present
    is_blocking: true
    minimum_approver_count: 2
    creator_vote_counts: false
    reset_on_source_push: true

- name: Require work item linking
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: work_item_linking
    state: present
    is_blocking: false

- name: Require comment resolution
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: comment_resolution
    state: present

- name: Require build validation
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: build_validation
    state: present
    build_definition_id: 123
    build_display_name: "PR Build Validation"
    build_valid_duration: 720

- name: Remove minimum reviewers policy
  basicPr0grammer.azure_devops.azure_devops_branch_policy:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    repository_id: "{{ repo_id }}"
    branch_name: "main"
    policy_type: minimum_reviewers
    state: absent
'''

RETURN = r'''
policy:
  description: Information about the branch policy
  returned: always
  type: dict
  contains:
    id:
      description: Policy configuration ID
      type: int
    type:
      description: Policy type information
      type: dict
    is_enabled:
      description: Whether the policy is enabled
      type: bool
    is_blocking:
      description: Whether the policy is blocking
      type: bool
    settings:
      description: Policy-specific settings
      type: dict
'''

from ansible.module_utils.basic import AnsibleModule
import os

# Policy Type IDs
POLICY_TYPE_IDS = {
    'minimum_reviewers': 'fa4e907d-c16b-4a4c-9dfa-4906e5d171dd',
    'work_item_linking': '40e92b44-2fe1-4dd6-b3d8-74a9c21d0c6e',
    'comment_resolution': 'c6a1889d-b943-4856-b76f-9e46bb6b0df2',
    'build_validation': '0609b952-1397-4640-95ec-e00a01b2c241',
    'required_reviewers': 'fd2167ab-b0be-447a-8ec8-39368250530e',
    'merge_strategy': 'fa4e907d-c16b-4a4c-9dfa-4916e5d171ab',
}


def normalize_branch_name(branch_name):
    """Normalize branch name to refs/heads/branch format"""
    if not branch_name.startswith('refs/'):
        return f'refs/heads/{branch_name}'
    return branch_name


def get_credentials(module):
    """Get authentication credentials"""
    from msrest.authentication import BasicAuthentication
    
    pat = module.params.get('personal_access_token')
    if not pat:
        pat = os.environ.get('AZURE_DEVOPS_PAT')
    
    if not pat:
        module.fail_json(msg="Personal Access Token is required. Provide via personal_access_token parameter or AZURE_DEVOPS_PAT environment variable")
    
    return BasicAuthentication('', pat)


def build_policy_settings(module, policy_type, repo_id, branch_ref):
    """Build policy settings based on policy type"""
    settings = {
        'scope': [{
            'repositoryId': repo_id,
            'refName': branch_ref,
            'matchKind': 'exact'
        }]
    }
    
    if policy_type == 'minimum_reviewers':
        settings['minimumApproverCount'] = module.params.get('minimum_approver_count', 1)
        settings['creatorVoteCounts'] = module.params.get('creator_vote_counts', False)
        settings['allowDownvotes'] = module.params.get('allow_downvotes', False)
        settings['resetOnSourcePush'] = module.params.get('reset_on_source_push', True)
    
    elif policy_type == 'build_validation':
        build_def_id = module.params.get('build_definition_id')
        if not build_def_id:
            module.fail_json(msg="build_definition_id is required for build_validation policy")
        
        settings['buildDefinitionId'] = build_def_id
        settings['displayName'] = module.params.get('build_display_name', 'Build Validation')
        settings['manualQueueOnly'] = module.params.get('build_manual_queue_only', False)
        settings['queueOnSourceUpdateOnly'] = module.params.get('build_queue_on_source_update_only', True)
        settings['validDuration'] = module.params.get('build_valid_duration', 720)
    
    elif policy_type == 'required_reviewers':
        reviewer_ids = module.params.get('required_reviewer_ids')
        if not reviewer_ids:
            module.fail_json(msg="required_reviewer_ids is required for required_reviewers policy")
        
        settings['requiredReviewerIds'] = reviewer_ids
        path_filters = module.params.get('path_filters', [])
        if path_filters:
            settings['filenamePatterns'] = path_filters
    
    elif policy_type == 'merge_strategy':
        settings['useSquashMerge'] = module.params.get('use_squash_merge', False)
    
    # work_item_linking and comment_resolution don't need additional settings beyond scope
    
    return settings


def find_existing_policy(policy_client, project, repo_id, branch_ref, policy_type_id):
    """Find existing policy configuration"""
    try:
        policies = policy_client.get_policy_configurations(project=project)
        
        for policy in policies:
            # Check if policy matches our criteria
            if policy.type.id != policy_type_id:
                continue
            
            if not policy.settings or 'scope' not in policy.settings:
                continue
            
            # Check if any scope matches our repository and branch
            for scope in policy.settings['scope']:
                if (scope.get('repositoryId') == repo_id and 
                    scope.get('refName') == branch_ref):
                    return policy
        
        return None
    except Exception as e:
        return None


def policy_to_dict(policy):
    """Convert policy object to dictionary"""
    return {
        'id': policy.id,
        'type': {
            'id': policy.type.id,
            'display_name': policy.type.display_name if hasattr(policy.type, 'display_name') else None
        },
        'is_enabled': policy.is_enabled,
        'is_blocking': policy.is_blocking,
        'settings': policy.settings,
        'url': policy.url if hasattr(policy, 'url') else None
    }


def create_policy(module, policy_client, project, repo_id, branch_ref, policy_type, policy_type_id):
    """Create a new branch policy"""
    try:
        from azure.devops.v7_1.policy.models import PolicyConfiguration, PolicyTypeRef
        
        settings = build_policy_settings(module, policy_type, repo_id, branch_ref)
        
        policy_config = PolicyConfiguration(
            is_enabled=module.params.get('is_enabled', True),
            is_blocking=module.params.get('is_blocking', True),
            type=PolicyTypeRef(id=policy_type_id),
            settings=settings
        )
        
        if not module.check_mode:
            created_policy = policy_client.create_policy_configuration(
                configuration=policy_config,
                project=project
            )
            return created_policy, True
        else:
            return None, True
            
    except Exception as e:
        module.fail_json(msg=f"Failed to create policy: {str(e)}")


def compare_settings(existing_settings, new_settings, policy_type):
    """Compare policy settings intelligently, checking only relevant fields"""
    # Check scope
    if existing_settings.get('scope') != new_settings.get('scope'):
        # Compare scope entries more carefully
        existing_scope = existing_settings.get('scope', [])
        new_scope = new_settings.get('scope', [])
        
        if len(existing_scope) != len(new_scope):
            return False
        
        for existing, new in zip(existing_scope, new_scope):
            if existing.get('repositoryId') != new.get('repositoryId'):
                return False
            if existing.get('refName') != new.get('refName'):
                return False
            # matchKind can vary (exact vs Exact), ignore it
    
    # Check policy-specific settings
    if policy_type == 'minimum_reviewers':
        if existing_settings.get('minimumApproverCount') != new_settings.get('minimumApproverCount'):
            return False
        if existing_settings.get('creatorVoteCounts') != new_settings.get('creatorVoteCounts'):
            return False
        if existing_settings.get('allowDownvotes') != new_settings.get('allowDownvotes'):
            return False
        if existing_settings.get('resetOnSourcePush') != new_settings.get('resetOnSourcePush'):
            return False
    
    elif policy_type == 'build_validation':
        if existing_settings.get('buildDefinitionId') != new_settings.get('buildDefinitionId'):
            return False
        if existing_settings.get('displayName') != new_settings.get('displayName'):
            return False
        if existing_settings.get('manualQueueOnly') != new_settings.get('manualQueueOnly'):
            return False
        if existing_settings.get('queueOnSourceUpdateOnly') != new_settings.get('queueOnSourceUpdateOnly'):
            return False
        if existing_settings.get('validDuration') != new_settings.get('validDuration'):
            return False
    
    elif policy_type == 'required_reviewers':
        if existing_settings.get('requiredReviewerIds') != new_settings.get('requiredReviewerIds'):
            return False
        if existing_settings.get('filenamePatterns') != new_settings.get('filenamePatterns'):
            return False
    
    elif policy_type == 'merge_strategy':
        if existing_settings.get('useSquashMerge') != new_settings.get('useSquashMerge'):
            return False
    
    # work_item_linking and comment_resolution only check scope
    return True


def update_policy(module, policy_client, project, existing_policy, repo_id, branch_ref, policy_type):
    """Update an existing branch policy"""
    try:
        settings = build_policy_settings(module, policy_type, repo_id, branch_ref)
        is_enabled = module.params.get('is_enabled', True)
        is_blocking = module.params.get('is_blocking', True)
        
        # Check if update is needed
        needs_update = False
        if existing_policy.is_enabled != is_enabled:
            needs_update = True
        if existing_policy.is_blocking != is_blocking:
            needs_update = True
        if not compare_settings(existing_policy.settings, settings, policy_type):
            needs_update = True
        
        if not needs_update:
            return existing_policy, False
        
        # Update policy
        existing_policy.is_enabled = is_enabled
        existing_policy.is_blocking = is_blocking
        existing_policy.settings = settings
        
        if not module.check_mode:
            updated_policy = policy_client.update_policy_configuration(
                configuration=existing_policy,
                project=project,
                configuration_id=existing_policy.id
            )
            return updated_policy, True
        else:
            return existing_policy, True
            
    except Exception as e:
        module.fail_json(msg=f"Failed to update policy: {str(e)}")


def delete_policy(module, policy_client, project, policy_id):
    """Delete a branch policy"""
    try:
        if not module.check_mode:
            policy_client.delete_policy_configuration(
                project=project,
                configuration_id=policy_id
            )
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete policy: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type='str', required=True),
            personal_access_token=dict(type='str', required=False, no_log=True),
            project=dict(type='str', required=True),
            repository_id=dict(type='str', required=True),
            branch_name=dict(type='str', required=True),
            policy_type=dict(
                type='str',
                required=True,
                choices=['minimum_reviewers', 'work_item_linking', 'comment_resolution', 
                        'build_validation', 'required_reviewers', 'merge_strategy']
            ),
            state=dict(type='str', default='present', choices=['present', 'absent']),
            is_blocking=dict(type='bool', default=True),
            is_enabled=dict(type='bool', default=True),
            # Minimum reviewers settings
            minimum_approver_count=dict(type='int'),
            creator_vote_counts=dict(type='bool', default=False),
            allow_downvotes=dict(type='bool', default=False),
            reset_on_source_push=dict(type='bool', default=True),
            # Build validation settings
            build_definition_id=dict(type='int'),
            build_display_name=dict(type='str'),
            build_manual_queue_only=dict(type='bool', default=False),
            build_queue_on_source_update_only=dict(type='bool', default=True),
            build_valid_duration=dict(type='int', default=720),
            # Required reviewers settings
            required_reviewer_ids=dict(type='list', elements='str'),
            path_filters=dict(type='list', elements='str'),
            # Merge strategy settings
            use_squash_merge=dict(type='bool'),
        ),
        supports_check_mode=True
    )

    try:
        from azure.devops.connection import Connection
    except ImportError:
        module.fail_json(msg="azure-devops package is required. Install it using: pip install azure-devops")

    organization_url = module.params['organization_url']
    project = module.params['project']
    repo_id = module.params['repository_id']
    branch_name = module.params['branch_name']
    policy_type = module.params['policy_type']
    state = module.params['state']

    # Normalize branch name
    branch_ref = normalize_branch_name(branch_name)
    
    # Get policy type ID
    policy_type_id = POLICY_TYPE_IDS[policy_type]

    # Authenticate
    credentials = get_credentials(module)
    connection = Connection(base_url=organization_url, creds=credentials)
    policy_client = connection.clients.get_policy_client()

    result = {
        'changed': False,
        'policy': None
    }

    try:
        # Find existing policy
        existing_policy = find_existing_policy(policy_client, project, repo_id, branch_ref, policy_type_id)

        if state == 'present':
            if not existing_policy:
                # Create new policy
                policy, changed = create_policy(module, policy_client, project, repo_id, 
                                              branch_ref, policy_type, policy_type_id)
                result['changed'] = changed
                if policy:
                    result['policy'] = policy_to_dict(policy)
                else:
                    result['policy'] = {'state': 'would_be_created'}
            else:
                # Update existing policy
                policy, changed = update_policy(module, policy_client, project, existing_policy,
                                              repo_id, branch_ref, policy_type)
                result['changed'] = changed
                result['policy'] = policy_to_dict(policy)
        
        elif state == 'absent':
            if existing_policy:
                # Delete policy
                changed = delete_policy(module, policy_client, project, existing_policy.id)
                result['changed'] = changed
                result['policy'] = {'state': 'deleted', 'id': existing_policy.id}
            else:
                result['policy'] = {'state': 'already_absent'}

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"An error occurred: {str(e)}")


if __name__ == '__main__':
    main()
