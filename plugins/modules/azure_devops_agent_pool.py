#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, basicPr0grammer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_agent_pool
short_description: Manage Azure DevOps agent pools
description:
  - Create, update, or delete agent pools in Azure DevOps
  - List agents in a pool
  - Get agent pool information and status
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
  pool_id:
    description:
      - ID of the agent pool
      - Required when updating or deleting a pool
    required: false
    type: int
  name:
    description:
      - Name of the agent pool
    required: false
    type: str
  state:
    description:
      - Desired state of the agent pool
    type: str
    choices: ['present', 'absent', 'info']
    default: present
  auto_provision:
    description:
      - Whether to auto-provision this agent pool to all projects
    type: bool
    default: false
  auto_size:
    description:
      - Whether the pool should automatically scale
    type: bool
  auto_update:
    description:
      - Whether agents should automatically update
    type: bool
    default: true
  list_agents:
    description:
      - Whether to list agents in the pool when getting pool info
    type: bool
    default: false
author:
  - basicPr0grammer
'''

EXAMPLES = r'''
- name: Create an agent pool
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/MyOrg"
    name: "MyAgentPool"
    state: present
    auto_provision: true
    auto_update: true

- name: Get agent pool information
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/MyOrg"
    pool_id: 10
    state: info
    list_agents: true
  register: pool_info

- name: Update agent pool settings
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/MyOrg"
    pool_id: 10
    auto_provision: false
    auto_update: true
    state: present

- name: Delete an agent pool
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/MyOrg"
    pool_id: 10
    state: absent

- name: List all agent pools
  basicPr0grammer.azure_devops.azure_devops_agent_pool:
    organization_url: "https://dev.azure.com/MyOrg"
    state: info
  register: all_pools
'''

RETURN = r'''
pool:
  description: Information about the agent pool
  returned: when state is present or info
  type: dict
  contains:
    id:
      description: Pool ID
      type: int
    name:
      description: Pool name
      type: str
    is_hosted:
      description: Whether this is a Microsoft-hosted pool
      type: bool
    size:
      description: Number of agents in the pool
      type: int
    auto_provision:
      description: Auto-provision setting
      type: bool
    auto_update:
      description: Auto-update setting
      type: bool
pools:
  description: List of all agent pools
  returned: when state is info and no pool_id specified
  type: list
agents:
  description: List of agents in the pool
  returned: when list_agents is true
  type: list
  elements: dict
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


def pool_to_dict(pool):
    """Convert agent pool object to dictionary"""
    if not pool:
        return None
    
    return {
        'id': pool.id,
        'name': pool.name,
        'is_hosted': pool.is_hosted if hasattr(pool, 'is_hosted') else False,
        'is_legacy': pool.is_legacy if hasattr(pool, 'is_legacy') else False,
        'pool_type': pool.pool_type if hasattr(pool, 'pool_type') else None,
        'size': pool.size if hasattr(pool, 'size') else 0,
        'auto_provision': pool.auto_provision if hasattr(pool, 'auto_provision') else False,
        'auto_update': pool.auto_update if hasattr(pool, 'auto_update') else True,
        'scope': pool.scope if hasattr(pool, 'scope') else None,
    }


def agent_to_dict(agent):
    """Convert agent object to dictionary"""
    if not agent:
        return None
    
    return {
        'id': agent.id,
        'name': agent.name,
        'version': agent.version if hasattr(agent, 'version') else None,
        'enabled': agent.enabled if hasattr(agent, 'enabled') else False,
        'status': agent.status if hasattr(agent, 'status') else None,
        'provisioning_state': agent.provisioning_state if hasattr(agent, 'provisioning_state') else None,
        'max_parallelism': agent.max_parallelism if hasattr(agent, 'max_parallelism') else 1,
    }


def get_pool_by_name(agent_client, pool_name):
    """Find a pool by name"""
    try:
        pools = agent_client.get_agent_pools()
        for pool in pools:
            if pool.name == pool_name:
                return pool
        return None
    except Exception:
        return None


def create_agent_pool(module, agent_client, pool_name):
    """Create a new agent pool"""
    try:
        from azure.devops.v7_1.task_agent.models import TaskAgentPool
        
        pool = TaskAgentPool(
            name=pool_name,
            auto_provision=module.params.get('auto_provision', False),
            auto_update=module.params.get('auto_update', True)
        )
        
        if not module.check_mode:
            created_pool = agent_client.add_agent_pool(pool=pool)
            return created_pool, True
        else:
            return None, True
            
    except Exception as e:
        module.fail_json(msg=f"Failed to create agent pool: {str(e)}")


def update_agent_pool(module, agent_client, pool_id, existing_pool):
    """Update an existing agent pool"""
    try:
        from azure.devops.v7_1.task_agent.models import TaskAgentPool
        
        auto_provision = module.params.get('auto_provision')
        auto_update = module.params.get('auto_update')
        
        # Check if update is needed
        needs_update = False
        if auto_provision is not None and existing_pool.auto_provision != auto_provision:
            needs_update = True
        if auto_update is not None and existing_pool.auto_update != auto_update:
            needs_update = True
        
        if not needs_update:
            return existing_pool, False
        
        # Build update object
        updated_pool = TaskAgentPool(
            id=pool_id,
            name=existing_pool.name,
            auto_provision=auto_provision if auto_provision is not None else existing_pool.auto_provision,
            auto_update=auto_update if auto_update is not None else existing_pool.auto_update
        )
        
        if not module.check_mode:
            result_pool = agent_client.update_agent_pool(pool=updated_pool, pool_id=pool_id)
            return result_pool, True
        else:
            return updated_pool, True
            
    except Exception as e:
        module.fail_json(msg=f"Failed to update agent pool: {str(e)}")


def delete_agent_pool(module, agent_client, pool_id):
    """Delete an agent pool"""
    try:
        if not module.check_mode:
            agent_client.delete_agent_pool(pool_id=pool_id)
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete agent pool: {str(e)}")


def get_pool_agents(agent_client, pool_id):
    """Get list of agents in a pool"""
    try:
        agents = agent_client.get_agents(pool_id=pool_id)
        return [agent_to_dict(agent) for agent in agents]
    except Exception as e:
        return []


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type='str', required=True),
            personal_access_token=dict(type='str', required=False, no_log=True),
            pool_id=dict(type='int', required=False),
            name=dict(type='str', required=False),
            state=dict(type='str', default='present', choices=['present', 'absent', 'info']),
            auto_provision=dict(type='bool', required=False),
            auto_size=dict(type='bool', required=False),
            auto_update=dict(type='bool', required=False),
            list_agents=dict(type='bool', default=False),
        ),
        supports_check_mode=True,
        required_if=[
            ('state', 'absent', ['pool_id']),
        ]
    )

    try:
        from azure.devops.connection import Connection
    except ImportError:
        module.fail_json(msg="azure-devops package is required. Install it using: pip install azure-devops")

    organization_url = module.params['organization_url']
    pool_id = module.params['pool_id']
    pool_name = module.params['name']
    state = module.params['state']
    list_agents = module.params['list_agents']

    # Authenticate
    credentials = get_credentials(module)
    connection = Connection(base_url=organization_url, creds=credentials)
    agent_client = connection.clients.get_task_agent_client()

    result = {
        'changed': False,
        'pool': None,
        'pools': None,
        'agents': None
    }

    try:
        # Get existing pool
        existing_pool = None
        if pool_id:
            try:
                existing_pool = agent_client.get_agent_pool(pool_id=pool_id)
            except Exception:
                if state != 'absent':
                    module.fail_json(msg=f"Agent pool {pool_id} not found")
        elif pool_name:
            existing_pool = get_pool_by_name(agent_client, pool_name)
        
        if state == 'info':
            if pool_id or (pool_name and pool_name != "Default"):
                # Get specific pool info
                if not existing_pool:
                    module.fail_json(msg=f"Agent pool not found")
                
                result['pool'] = pool_to_dict(existing_pool)
                
                if list_agents:
                    result['agents'] = get_pool_agents(agent_client, existing_pool.id)
            else:
                # List all pools
                pools = agent_client.get_agent_pools()
                result['pools'] = [pool_to_dict(pool) for pool in pools]
        
        elif state == 'present':
            if existing_pool:
                # Update existing pool
                if pool_id:
                    pool, changed = update_agent_pool(module, agent_client, pool_id, existing_pool)
                    result['changed'] = changed
                    if pool:
                        result['pool'] = pool_to_dict(pool)
                        if list_agents:
                            result['agents'] = get_pool_agents(agent_client, pool.id)
                else:
                    # Pool exists, no update needed if only name provided
                    result['pool'] = pool_to_dict(existing_pool)
                    if list_agents:
                        result['agents'] = get_pool_agents(agent_client, existing_pool.id)
            else:
                # Create new pool
                if not pool_name:
                    module.fail_json(msg="name is required when creating a new agent pool")
                
                pool, changed = create_agent_pool(module, agent_client, pool_name)
                result['changed'] = changed
                if pool:
                    result['pool'] = pool_to_dict(pool)
                elif module.check_mode:
                    result['pool'] = {'state': 'would_be_created', 'name': pool_name}
        
        elif state == 'absent':
            if existing_pool:
                changed = delete_agent_pool(module, agent_client, pool_id)
                result['changed'] = changed
                result['pool'] = {'state': 'deleted', 'id': pool_id}
            else:
                result['pool'] = {'state': 'already_absent'}

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"An error occurred: {str(e)}")


if __name__ == '__main__':
    main()
