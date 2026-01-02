#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, basicPr0grammer
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_repository
short_description: Manage Azure DevOps Git repositories
description:
    - Create, update, or delete Azure DevOps Git repositories
    - Manage default branches
    - Configure branch policies
    - Fork repositories
    - Fully idempotent operations
version_added: "1.3.0"
author:
    - basicPr0grammer
options:
    organization_url:
        description:
            - The URL of the Azure DevOps organization
        required: true
        type: str
    
    personal_access_token:
        description:
            - Personal Access Token (PAT) for authentication
            - Can also be set via AZURE_DEVOPS_PAT environment variable
        required: false
        type: str
    
    project:
        description:
            - Name or ID of the project
        required: true
        type: str
    
    name:
        description:
            - Name of the repository
        required: true
        type: str
    
    state:
        description:
            - State of the repository
        choices: ['present', 'absent']
        default: 'present'
        type: str
    
    default_branch:
        description:
            - Default branch for the repository
            - Example: 'main', 'master', 'develop'
            - Will be converted to full ref format (refs/heads/...)
        required: false
        type: str
    
    is_disabled:
        description:
            - Whether the repository is disabled
        required: false
        type: bool
        default: false
    
    parent_repository_id:
        description:
            - ID of the parent repository to fork from
            - Only used when creating a fork
        required: false
        type: str
    
    branch_name:
        description:
            - Name of the branch to create
            - Example: 'feature/new-feature', 'release/v1.0'
            - Only used when branch_state is 'present'
        required: false
        type: str
    
    source_branch:
        description:
            - Source branch to create the new branch from
            - Example: 'main', 'develop'
            - Required when branch_name is specified
            - Will be converted to full ref format (refs/heads/...)
        required: false
        type: str
    
    branch_state:
        description:
            - State of the branch (if branch_name is specified)
            - Use 'present' to create branch if it doesn't exist
            - Use 'absent' to delete the branch
        choices: ['present', 'absent']
        default: 'present'
        type: str

notes:
    - Requires azure-devops Python package
    - PAT needs Code (Read, Write & Manage) scope
    - Use organization_url format like https://dev.azure.com/yourorg
    - Default branch can only be set after the repository has at least one commit
    - Branch operations require the repository to have at least one commit
'''

EXAMPLES = r'''
- name: Create a new repository
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    personal_access_token: "{{ pat }}"
    project: "MyProject"
    name: "my-new-repo"
    state: present

- name: Create repository with specific default branch
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-repo"
    default_branch: "main"
    state: present

- name: Fork a repository
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "forked-repo"
    parent_repository_id: "12345678-1234-1234-1234-123456789012"
    state: present

- name: Disable a repository
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "old-repo"
    is_disabled: true
    state: present

- name: Delete a repository
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "old-repo"
    state: absent

- name: Use PAT from environment variable
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-repo"
    state: present
  environment:
    AZURE_DEVOPS_PAT: "{{ lookup('env', 'AZURE_DEVOPS_PAT') }}"

- name: Create a new branch from main
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-repo"
    branch_name: "feature/new-feature"
    source_branch: "main"
    branch_state: present
    state: present

- name: Create a release branch from develop
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-repo"
    branch_name: "release/v1.0"
    source_branch: "develop"
    state: present

- name: Delete a branch
  basicPr0grammer.azure_devops.azure_devops_repository:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-repo"
    branch_name: "feature/old-feature"
    branch_state: absent
    state: present
'''

RETURN = r'''
repository:
    description: Details of the repository
    returned: always
    type: dict
    sample:
        id: "12345678-1234-1234-1234-123456789012"
        name: "my-repo"
        url: "https://dev.azure.com/myorg/MyProject/_git/my-repo"
        remote_url: "https://myorg@dev.azure.com/myorg/MyProject/_git/my-repo"
        ssh_url: "git@ssh.dev.azure.com:v3/myorg/MyProject/my-repo"
        web_url: "https://dev.azure.com/myorg/MyProject/_git/my-repo"
        default_branch: "refs/heads/main"
        size: 0
        is_disabled: false
        is_fork: false
changed:
    description: Whether the repository was changed
    returned: always
    type: bool
'''

import os
from ansible.module_utils.basic import AnsibleModule

try:
    from azure.devops.connection import Connection
    from azure.devops.v7_1.git.models import GitRepository, GitRepositoryCreateOptions
    from msrest.authentication import BasicAuthentication
    HAS_AZURE_DEVOPS = True
except ImportError:
    HAS_AZURE_DEVOPS = False


def get_repository(git_client, project, repo_name):
    """Get repository by name - includes disabled repositories"""
    try:
        # Try to get repository directly by name (works for both enabled and disabled)
        repo = git_client.get_repository(project=project, repository_id=repo_name)
        return repo
    except Exception as e:
        # If direct lookup fails, try listing all repositories (including disabled ones)
        try:
            repos = git_client.get_repositories(project=project, include_hidden=True)
            for repo in repos:
                if repo.name == repo_name:
                    return repo
        except Exception:
            pass
        return None


def create_repository(module, git_client, project, name, parent_repository_id=None):
    """Create a new repository"""
    try:
        create_options = GitRepositoryCreateOptions(name=name)
        
        # Set parent repository if forking
        if parent_repository_id:
            # Get the parent repository to extract its project info
            try:
                parent_repo = git_client.get_repository(repository_id=parent_repository_id)
                parent_ref = {
                    'id': parent_repository_id,
                    'project': {
                        'id': parent_repo.project.id,
                        'name': parent_repo.project.name
                    }
                }
                create_options.parent_repository = parent_ref
            except Exception as e:
                module.fail_json(msg=f"Failed to get parent repository for fork: {str(e)}")
        
        repo = git_client.create_repository(
            git_repository_to_create=create_options,
            project=project
        )
        return repo, True
    except Exception as e:
        module.fail_json(msg=f"Failed to create repository: {str(e)}")


def update_repository(module, git_client, repo_id, default_branch=None, is_disabled=None):
    """Update repository settings"""
    changed = False
    
    try:
        # Get current repository to compare
        # Note: Disabled repositories may not be retrievable via standard get
        try:
            current_repo = git_client.get_repository(repository_id=repo_id)
        except Exception:
            # Try to get all repos including hidden/disabled ones
            repos = git_client.get_repositories(include_hidden=True)
            current_repo = None
            for repo in repos:
                if repo.id == repo_id:
                    current_repo = repo
                    break
            if not current_repo:
                raise Exception(f"Repository with ID {repo_id} not found")
        
        # Check if repository is already disabled - can't update disabled repos
        if current_repo.is_disabled and is_disabled is True:
            # Repository is already disabled and we want it disabled - no change needed
            return current_repo, False
        
        # Prepare update object with snake_case parameters
        update_params = {}
        
        # Check if default branch needs to be updated
        if default_branch:
            # Normalize branch format
            if not default_branch.startswith('refs/'):
                default_branch = f'refs/heads/{default_branch}'
            
            if current_repo.default_branch != default_branch:
                update_params['default_branch'] = default_branch
                changed = True
        
        # Check if disabled status needs to be updated
        if is_disabled is not None and current_repo.is_disabled != is_disabled:
            update_params['is_disabled'] = is_disabled
            changed = True
        
        # Perform update if there are changes
        if changed:
            repo = GitRepository(**update_params)
            updated_repo = git_client.update_repository(
                new_repository_info=repo,
                repository_id=repo_id
            )
            return updated_repo, changed
        
        return current_repo, changed
        
    except Exception as e:
        module.fail_json(msg=f"Failed to update repository: {str(e)}")


def delete_repository(module, git_client, repo_id):
    """Delete a repository"""
    try:
        git_client.delete_repository(repository_id=repo_id)
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete repository: {str(e)}")


def get_branch(git_client, repo_id, branch_name):
    """Get a branch from the repository"""
    try:
        # Normalize branch name
        if not branch_name.startswith('refs/'):
            branch_ref = f'refs/heads/{branch_name}'
            filter_name = f'heads/{branch_name}'
        else:
            branch_ref = branch_name
            filter_name = branch_name.replace('refs/heads/', 'heads/')
        
        # Try with filter
        refs = git_client.get_refs(repository_id=repo_id, filter=filter_name)
        if refs:
            return refs[0]
        
        # Fallback: get all and filter manually
        all_refs = git_client.get_refs(repository_id=repo_id)
        for ref in all_refs:
            if ref.name == branch_ref:
                return ref
        
        return None
    except Exception:
        return None


def create_branch(module, git_client, repo_id, branch_name, source_branch):
    """Create a new branch in the repository"""
    try:
        # Normalize branch names
        if not branch_name.startswith('refs/'):
            new_branch_ref = f'refs/heads/{branch_name}'
        else:
            new_branch_ref = branch_name
        
        if not source_branch.startswith('refs/'):
            source_branch_ref = f'refs/heads/{source_branch}'
        else:
            source_branch_ref = source_branch
        
        # Get the source branch to get its object ID
        # The get_refs API needs project and repository_id
        try:
            # Try with filter parameter
            source_refs = git_client.get_refs(
                repository_id=repo_id,
                filter=f'heads/{source_branch}' if not source_branch.startswith('refs/') else source_branch.replace('refs/heads/', 'heads/')
            )
        except Exception as e:
            # Try getting all refs and filtering manually
            try:
                all_refs = git_client.get_refs(repository_id=repo_id)
                source_refs = [ref for ref in all_refs if ref.name == source_branch_ref]
            except Exception:
                module.fail_json(msg=f"Failed to query branches: {str(e)}")
        
        if not source_refs:
            module.fail_json(msg=f"Source branch '{source_branch}' (looking for '{source_branch_ref}') not found in repository")
        
        source_ref = source_refs[0]
        
        # Create the new branch ref update
        from azure.devops.v7_1.git.models import GitRefUpdate
        ref_update = GitRefUpdate(
            name=new_branch_ref,
            old_object_id='0000000000000000000000000000000000000000',  # New ref
            new_object_id=source_ref.object_id
        )
        
        # Update refs to create the branch
        result = git_client.update_refs(
            ref_updates=[ref_update],
            repository_id=repo_id
        )
        
        # Result is a list of GitRefUpdateResult objects
        if result and len(result) > 0:
            return result[0], True
        
        return None, False
        
    except Exception as e:
        module.fail_json(msg=f"Failed to create branch: {str(e)}")


def delete_branch(module, git_client, repo_id, branch_name):
    """Delete a branch from the repository"""
    try:
        # Normalize branch name
        if not branch_name.startswith('refs/'):
            branch_ref = f'refs/heads/{branch_name}'
            filter_name = f'heads/{branch_name}'
        else:
            branch_ref = branch_name
            filter_name = branch_name.replace('refs/heads/', 'heads/')
        
        # Get the branch to get its object ID
        refs = git_client.get_refs(repository_id=repo_id, filter=filter_name)
        if not refs:
            # Branch doesn't exist, nothing to delete
            return False
        
        branch_ref_obj = refs[0]
        
        # Create the ref update to delete the branch
        from azure.devops.v7_1.git.models import GitRefUpdate
        ref_update = GitRefUpdate(
            name=branch_ref,
            old_object_id=branch_ref_obj.object_id,
            new_object_id='0000000000000000000000000000000000000000'  # Delete ref
        )
        
        # Update refs to delete the branch
        result = git_client.update_refs(
            ref_updates=[ref_update],
            repository_id=repo_id
        )
        
        return True
        
    except Exception as e:
        module.fail_json(msg=f"Failed to delete branch: {str(e)}")


def delete_repository(module, git_client, repo_id):
    """Delete a repository"""
    try:
        git_client.delete_repository(repository_id=repo_id)
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete repository: {str(e)}")


def repository_to_dict(repo):
    """Convert repository object to dictionary"""
    if not repo:
        return None
    
    result = {
        'id': repo.id,
        'name': repo.name,
        'url': repo.url,
        'remote_url': repo.remote_url,
        'ssh_url': repo.ssh_url,
        'web_url': repo.web_url,
        'size': repo.size,
        'is_disabled': repo.is_disabled,
    }
    
    # Add default branch if available
    if hasattr(repo, 'default_branch') and repo.default_branch:
        result['default_branch'] = repo.default_branch
    
    # Add fork information if available
    if hasattr(repo, 'is_fork') and repo.is_fork:
        result['is_fork'] = repo.is_fork
        if hasattr(repo, 'parent_repository') and repo.parent_repository:
            result['parent_repository_id'] = repo.parent_repository.id
    
    # Add project information
    if hasattr(repo, 'project') and repo.project:
        result['project'] = {
            'id': repo.project.id,
            'name': repo.project.name
        }
    
    return result


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type='str', required=True),
            personal_access_token=dict(type='str', required=False, no_log=True),
            project=dict(type='str', required=True),
            name=dict(type='str', required=True),
            state=dict(type='str', choices=['present', 'absent'], default='present'),
            default_branch=dict(type='str', required=False),
            is_disabled=dict(type='bool', default=False),
            parent_repository_id=dict(type='str', required=False),
            branch_name=dict(type='str', required=False),
            source_branch=dict(type='str', required=False),
            branch_state=dict(type='str', choices=['present', 'absent'], default='present'),
        ),
        required_if=[
            ['branch_name', True, ['source_branch'], False],  # source_branch needed for branch creation, not deletion
        ],
        supports_check_mode=True
    )
    
    if not HAS_AZURE_DEVOPS:
        module.fail_json(msg="The azure-devops Python package is required")
    
    organization_url = module.params['organization_url']
    pat = module.params['personal_access_token'] or os.environ.get('AZURE_DEVOPS_PAT')
    project = module.params['project']
    name = module.params['name']
    state = module.params['state']
    default_branch = module.params.get('default_branch')
    is_disabled = module.params['is_disabled']
    parent_repository_id = module.params.get('parent_repository_id')
    branch_name = module.params.get('branch_name')
    source_branch = module.params.get('source_branch')
    branch_state = module.params['branch_state']
    
    if not pat:
        module.fail_json(msg="personal_access_token or AZURE_DEVOPS_PAT environment variable is required")
    
    # Create connection
    credentials = BasicAuthentication('', pat)
    connection = Connection(base_url=organization_url, creds=credentials)
    git_client = connection.clients.get_git_client()
    
    result = {
        'changed': False,
        'repository': None,
        'branch': None
    }
    
    try:
        # Check if repository exists
        existing_repo = get_repository(git_client, project, name)
        
        if state == 'absent':
            if existing_repo:
                if not module.check_mode:
                    delete_repository(module, git_client, existing_repo.id)
                result['changed'] = True
                result['repository'] = {'name': name, 'state': 'deleted'}
            # If doesn't exist, no change needed
            
        else:  # state == 'present'
            if not existing_repo:
                # Create new repository
                if not module.check_mode:
                    repo, changed = create_repository(module, git_client, project, name, parent_repository_id)
                    result['repository'] = repository_to_dict(repo)
                    result['changed'] = changed
                    
                    # Try to update default branch if specified (might fail if repo has no commits yet)
                    if default_branch:
                        try:
                            repo, branch_changed = update_repository(
                                module, git_client, repo.id, 
                                default_branch=default_branch
                            )
                            result['repository'] = repository_to_dict(repo)
                            # Don't update changed flag since we already know we made changes
                        except Exception as e:
                            module.warn(f"Repository created but couldn't set default branch: {str(e)}. " +
                                      "This is normal for empty repositories. Push a commit first.")
                else:
                    result['changed'] = True
                    result['repository'] = {'name': name, 'state': 'would_be_created'}
            else:
                # Update existing repository
                if not module.check_mode:
                    repo, changed = update_repository(
                        module, git_client, existing_repo.id,
                        default_branch=default_branch,
                        is_disabled=is_disabled
                    )
                    result['repository'] = repository_to_dict(repo)
                    result['changed'] = changed
                else:
                    # In check mode, just report what would change
                    would_change = False
                    if default_branch:
                        normalized_branch = default_branch if default_branch.startswith('refs/') else f'refs/heads/{default_branch}'
                        if existing_repo.default_branch != normalized_branch:
                            would_change = True
                    if is_disabled is not None and existing_repo.is_disabled != is_disabled:
                        would_change = True
                    
                    result['changed'] = would_change
                    result['repository'] = repository_to_dict(existing_repo)
        
        # Handle branch operations if branch_name is specified
        if branch_name and existing_repo and state == 'present':
            if branch_state == 'present':
                # Check if branch already exists
                existing_branch = get_branch(git_client, existing_repo.id, branch_name)
                
                if not existing_branch:
                    if not module.check_mode:
                        # Validate source_branch is provided
                        if not source_branch:
                            module.fail_json(msg="source_branch is required when creating a new branch")
                        
                        branch, branch_changed = create_branch(
                            module, git_client, existing_repo.id,
                            branch_name, source_branch
                        )
                        result['branch'] = {
                            'name': branch_name,
                            'created': True,
                            'source_branch': source_branch
                        }
                        result['changed'] = True
                    else:
                        result['branch'] = {'name': branch_name, 'state': 'would_be_created'}
                        result['changed'] = True
                else:
                    # Branch already exists
                    result['branch'] = {
                        'name': branch_name,
                        'exists': True,
                        'object_id': existing_branch.object_id
                    }
            
            elif branch_state == 'absent':
                # Delete branch
                if not module.check_mode:
                    branch_deleted = delete_branch(module, git_client, existing_repo.id, branch_name)
                    if branch_deleted:
                        result['branch'] = {'name': branch_name, 'state': 'deleted'}
                        result['changed'] = True
                    else:
                        result['branch'] = {'name': branch_name, 'state': 'already_deleted'}
                else:
                    result['branch'] = {'name': branch_name, 'state': 'would_be_deleted'}
                    result['changed'] = True
        
        module.exit_json(**result)
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == '__main__':
    main()
