#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, basicPr0grammer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_service_hook
short_description: Manage Azure DevOps Service Hooks (Webhooks)
description:
  - Create, update, or delete Azure DevOps Service Hook subscriptions
  - Send webhooks when events occur (work items, pull requests, builds, etc.)
  - Support for multiple consumers including Web Hooks, Slack, Teams, etc.
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
      - Required for most event types
    required: false
    type: str
  subscription_id:
    description:
      - ID of the subscription to update or delete
    required: false
    type: str
  event_type:
    description:
      - Type of event to subscribe to
    required: false
    type: str
    choices:
      - workitem.created
      - workitem.updated
      - workitem.commented
      - workitem.deleted
      - workitem.restored
      - git.push
      - git.pullrequest.created
      - git.pullrequest.updated
      - build.complete
      - release.deployment.completed
  consumer_type:
    description:
      - Type of consumer (where to send the webhook)
    required: false
    type: str
    choices:
      - webHooks
      - slack
      - teams
      - azureServiceBus
      - azureStorageQueue
    default: webHooks
  webhook_url:
    description:
      - URL to send the webhook to (for webHooks consumer)
    required: false
    type: str
  state:
    description:
      - Desired state of the subscription
    type: str
    choices: ['present', 'absent', 'info']
    default: present
  work_item_type:
    description:
      - Filter by work item type (User Story, Bug, Task, etc.)
    required: false
    type: str
  area_path:
    description:
      - Filter by area path
    required: false
    type: str
  field_name:
    description:
      - Filter by specific field name that changed
    required: false
    type: str
author:
  - basicPr0grammer
'''

EXAMPLES = r'''
- name: Create webhook for User Story updates
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    event_type: workitem.updated
    consumer_type: webHooks
    webhook_url: "https://my-server.com/webhook/workitems"
    work_item_type: "User Story"
    state: present

- name: Create webhook for all work item changes
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    event_type: workitem.updated
    consumer_type: webHooks
    webhook_url: "https://my-server.com/webhook/all-workitems"
    state: present

- name: Create webhook for Bug creation
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    event_type: workitem.created
    consumer_type: webHooks
    webhook_url: "https://my-server.com/webhook/new-bugs"
    work_item_type: "Bug"
    state: present

- name: Create Slack notification for PR updates
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/MyOrg"
    project: "MyProject"
    event_type: git.pullrequest.updated
    consumer_type: slack
    webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    state: present

- name: List all service hook subscriptions
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/MyOrg"
    state: info
  register: hooks

- name: Delete a service hook
  basicPr0grammer.azure_devops.azure_devops_service_hook:
    organization_url: "https://dev.azure.com/MyOrg"
    subscription_id: "{{ hook_id }}"
    state: absent
'''

RETURN = r'''
subscription:
  description: Information about the service hook subscription
  returned: when state is present or info
  type: dict
  contains:
    id:
      description: Subscription ID
      type: str
    event_type:
      description: Event type
      type: str
    consumer_id:
      description: Consumer ID
      type: str
    status:
      description: Subscription status
      type: str
    url:
      description: Subscription URL
      type: str
subscriptions:
  description: List of all subscriptions
  returned: when state is info and no subscription_id specified
  type: list
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


def subscription_to_dict(subscription):
    """Convert subscription object to dictionary"""
    if not subscription:
        return None
    
    return {
        'id': subscription.id,
        'event_type': subscription.event_type if hasattr(subscription, 'event_type') else None,
        'event_description': subscription.event_description if hasattr(subscription, 'event_description') else None,
        'consumer_id': subscription.consumer_id if hasattr(subscription, 'consumer_id') else None,
        'consumer_action_id': subscription.consumer_action_id if hasattr(subscription, 'consumer_action_id') else None,
        'action_description': subscription.action_description if hasattr(subscription, 'action_description') else None,
        'publisher_id': subscription.publisher_id if hasattr(subscription, 'publisher_id') else None,
        'status': subscription.status if hasattr(subscription, 'status') else None,
        'url': subscription.url if hasattr(subscription, 'url') else None,
        'created_date': subscription.created_date if hasattr(subscription, 'created_date') else None,
    }


def get_project_id(connection, project_name):
    """Get project ID from project name"""
    if not project_name:
        return None
    
    try:
        core_client = connection.clients.get_core_client()
        project = core_client.get_project(project_name)
        return project.id
    except Exception:
        return None


def build_publisher_inputs(module, project_id):
    """Build publisher inputs based on event type and filters"""
    publisher_inputs = {}
    
    # Add project filter
    if project_id:
        publisher_inputs['projectId'] = project_id
    
    # Add work item type filter
    if module.params.get('work_item_type'):
        publisher_inputs['workItemType'] = module.params['work_item_type']
    
    # Add area path filter
    if module.params.get('area_path'):
        publisher_inputs['areaPath'] = module.params['area_path']
    
    # Add field name filter for work item updates
    if module.params.get('field_name'):
        publisher_inputs['changedFields'] = module.params['field_name']
    
    return publisher_inputs


def build_consumer_inputs(module, consumer_type):
    """Build consumer inputs based on consumer type"""
    consumer_inputs = {}
    
    if consumer_type == 'webHooks':
        webhook_url = module.params.get('webhook_url')
        if not webhook_url:
            module.fail_json(msg="webhook_url is required for webHooks consumer")
        consumer_inputs['url'] = webhook_url
    elif consumer_type == 'slack':
        webhook_url = module.params.get('webhook_url')
        if not webhook_url:
            module.fail_json(msg="webhook_url is required for slack consumer")
        consumer_inputs['url'] = webhook_url
    elif consumer_type == 'teams':
        webhook_url = module.params.get('webhook_url')
        if not webhook_url:
            module.fail_json(msg="webhook_url is required for teams consumer")
        consumer_inputs['url'] = webhook_url
    
    return consumer_inputs


def get_consumer_action_id(hooks_client, consumer_type):
    """Get the consumer action ID for a consumer type"""
    consumer_actions = hooks_client.list_consumer_actions(consumer_id=consumer_type)
    
    if consumer_actions:
        # Return the first/default action
        return consumer_actions[0].id
    
    return None


def create_subscription(module, hooks_client, event_type, consumer_type, project_id):
    """Create a new service hook subscription"""
    try:
        from azure.devops.v7_1.service_hooks.models import Subscription
        
        publisher_inputs = build_publisher_inputs(module, project_id)
        consumer_inputs = build_consumer_inputs(module, consumer_type)
        consumer_action_id = get_consumer_action_id(hooks_client, consumer_type)
        
        if not consumer_action_id:
            module.fail_json(msg=f"Could not find consumer action for {consumer_type}")
        
        subscription = Subscription(
            publisher_id='tfs',
            event_type=event_type,
            resource_version='1.0',
            consumer_id=consumer_type,
            consumer_action_id=consumer_action_id,
            publisher_inputs=publisher_inputs,
            consumer_inputs=consumer_inputs
        )
        
        if not module.check_mode:
            created_sub = hooks_client.create_subscription(subscription=subscription)
            return created_sub, True
        else:
            return None, True
            
    except Exception as e:
        module.fail_json(msg=f"Failed to create subscription: {str(e)}")


def find_existing_subscription(hooks_client, event_type, webhook_url, publisher_inputs):
    """Find existing subscription matching criteria"""
    try:
        subscriptions = hooks_client.list_subscriptions()
        
        for sub in subscriptions:
            # Match event type
            if sub.event_type != event_type:
                continue
            
            # Match webhook URL if webHooks consumer
            if sub.consumer_id == 'webHooks':
                if sub.consumer_inputs and sub.consumer_inputs.get('url') == webhook_url:
                    # Check publisher inputs match
                    if sub.publisher_inputs:
                        matches = True
                        for key, value in publisher_inputs.items():
                            if sub.publisher_inputs.get(key) != value:
                                matches = False
                                break
                        if matches:
                            return sub
        
        return None
    except Exception:
        return None


def delete_subscription(module, hooks_client, subscription_id):
    """Delete a service hook subscription"""
    try:
        if not module.check_mode:
            hooks_client.delete_subscription(subscription_id=subscription_id)
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete subscription: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type='str', required=True),
            personal_access_token=dict(type='str', required=False, no_log=True),
            project=dict(type='str', required=False),
            subscription_id=dict(type='str', required=False),
            event_type=dict(
                type='str',
                required=False,
                choices=['workitem.created', 'workitem.updated', 'workitem.commented',
                        'workitem.deleted', 'workitem.restored', 'git.push',
                        'git.pullrequest.created', 'git.pullrequest.updated',
                        'build.complete', 'release.deployment.completed']
            ),
            consumer_type=dict(
                type='str',
                default='webHooks',
                choices=['webHooks', 'slack', 'teams', 'azureServiceBus', 'azureStorageQueue']
            ),
            webhook_url=dict(type='str', required=False),
            state=dict(type='str', default='present', choices=['present', 'absent', 'info']),
            work_item_type=dict(type='str', required=False),
            area_path=dict(type='str', required=False),
            field_name=dict(type='str', required=False),
        ),
        supports_check_mode=True,
        required_if=[
            ('state', 'absent', ['subscription_id']),
            ('state', 'present', ['event_type']),
        ]
    )

    try:
        from azure.devops.connection import Connection
    except ImportError:
        module.fail_json(msg="azure-devops package is required. Install it using: pip install azure-devops")

    organization_url = module.params['organization_url']
    project = module.params['project']
    subscription_id = module.params['subscription_id']
    event_type = module.params['event_type']
    consumer_type = module.params['consumer_type']
    webhook_url = module.params['webhook_url']
    state = module.params['state']

    # Authenticate
    credentials = get_credentials(module)
    connection = Connection(base_url=organization_url, creds=credentials)
    hooks_client = connection.clients.get_service_hooks_client()
    
    # Get project ID if project name provided
    project_id = None
    if project:
        project_id = get_project_id(connection, project)
        if not project_id:
            module.fail_json(msg=f"Could not find project: {project}")

    result = {
        'changed': False,
        'subscription': None,
        'subscriptions': None
    }

    try:
        if state == 'info':
            if subscription_id:
                # Get specific subscription
                sub = hooks_client.get_subscription(subscription_id=subscription_id)
                result['subscription'] = subscription_to_dict(sub)
            else:
                # List all subscriptions
                subs = hooks_client.list_subscriptions()
                result['subscriptions'] = [subscription_to_dict(s) for s in subs]
        
        elif state == 'present':
            # Check if subscription already exists
            publisher_inputs = build_publisher_inputs(module, project_id)
            existing_sub = find_existing_subscription(hooks_client, event_type, webhook_url, publisher_inputs)
            
            if existing_sub:
                # Subscription already exists
                result['subscription'] = subscription_to_dict(existing_sub)
            else:
                # Create new subscription
                sub, changed = create_subscription(module, hooks_client, event_type, consumer_type, project_id)
                result['changed'] = changed
                if sub:
                    result['subscription'] = subscription_to_dict(sub)
                elif module.check_mode:
                    result['subscription'] = {'state': 'would_be_created'}
        
        elif state == 'absent':
            # Check if subscription exists
            try:
                existing_sub = hooks_client.get_subscription(subscription_id=subscription_id)
                changed = delete_subscription(module, hooks_client, subscription_id)
                result['changed'] = changed
                result['subscription'] = {'state': 'deleted', 'id': subscription_id}
            except Exception:
                result['subscription'] = {'state': 'already_absent'}

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg=f"An error occurred: {str(e)}")


if __name__ == '__main__':
    main()
