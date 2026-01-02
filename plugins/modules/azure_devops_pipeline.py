#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, basicPr0grammer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: azure_devops_pipeline
short_description: Manage Azure DevOps pipelines
version_added: "1.0.0"
description:
    - Create, update, delete, and run Azure DevOps pipelines
    - Supports specifying branch for pipeline execution
    - Can wait for pipeline run completion
    - Supports passing variables and template parameters to pipeline runs

options:
    organization_url:
        description:
            - The URL of the Azure DevOps organization
            - Example: https://dev.azure.com/your-organization
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
            - The name or ID of the Azure DevOps project
        required: true
        type: str
    
    name:
        description:
            - Name of the pipeline
        required: true
        type: str
    
    state:
        description:
            - Desired state of the pipeline
            - Use "present" to create or update
            - Use "absent" to delete
            - Use "run" to trigger a pipeline run
        required: false
        type: str
        default: present
        choices: ["present", "absent", "run"]
    
    folder:
        description:
            - Folder path for the pipeline (e.g., "\\MyFolder" or "\\MyFolder\\SubFolder")
            - Root folder is "\\"
        required: false
        type: str
        default: "\\"
    
    repository_id:
        description:
            - The ID of the repository containing the YAML file
            - Required when state is "present" and pipeline doesn"t exist
        required: false
        type: str
    
    repository_name:
        description:
            - The name of the repository (alternative to repository_id)
            - Will be converted to ID automatically
        required: false
        type: str
    
    repository_type:
        description:
            - Type of repository
        required: false
        type: str
        default: "azureReposGit"
        choices:
          - "azureReposGit"
          - "github"
          - "gitHub"
          - "tfsgit"
          - "tfsversioncontrol"
    
    yaml_path:
        description:
            - Path to the YAML file in the repository
            - "Example: /azure-pipelines.yml or /pipelines/build.yml"
            - Required when state is "present" and pipeline doesn"t exist
        required: false
        type: str
    
    default_branch:
        description:
            - Default branch for the pipeline definition
            - Used when creating the pipeline to specify which branch contains the YAML file
            - 'Example: main, develop, dev or refs/heads/main'
        required: false
        type: str
        default: "main"
    
    branch:
        description:
            - Branch name for running the pipeline
            - Used only when state is "run"
            - If not specified, uses the pipeline"s default branch
        required: false
        type: str
    
    variables:
        description:
            - Dictionary of runtime variables to pass to the pipeline run
            - Variables must be defined in your YAML pipeline to be used
            - For passing values without pre-defining them, use template_parameters instead
            - Only used when state is "run"
            - Note that Build API has limited support for runtime variables
        required: false
        type: dict
    
    template_parameters:
        description:
            - Dictionary of template parameters to pass to the pipeline run
            - Template parameters must be defined in your YAML pipeline with "parameters:" section
            - This is the recommended way to pass values to YAML pipelines
            - Only used when state is "run"
        required: false
        type: dict
    
    wait_for_completion:
        description:
            - Whether to wait for the pipeline run to complete
            - Only used when state is "run"
        required: false
        type: bool
        default: false
    
    wait_timeout:
        description:
            - Maximum time to wait for pipeline completion in seconds
            - Only used when wait_for_completion is true
        required: false
        type: int
        default: 600

author:
    - basicPr0grammer
'''

EXAMPLES = r'''
# Create a new pipeline
- name: Create Azure DevOps pipeline
  basicPr0grammer.azure_devops.azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    personal_access_token: "{{ pat }}"
    project: "MyProject"
    name: "my-build-pipeline"
    folder: "\\Builds"
    repository_id: "12345678-1234-1234-1234-123456789012"
    repository_type: "azureReposGit"
    yaml_path: "/azure-pipelines.yml"
    default_branch: "main"
    state: present

# Create a pipeline using repository name and different branch
- name: Create pipeline with repo name on dev branch
  basicPr0grammer.azure_devops.azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-app-pipeline"
    repository_name: "my-repo"
    yaml_path: "/pipelines/build.yml"
    default_branch: "dev"
    state: present

# Run a pipeline
- name: Run pipeline
  basicPr0grammer.azure_devops.azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    state: run

# Run pipeline on specific branch with variables
- name: Run pipeline on feature branch
  basicPr0grammer.azure_devops.azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    branch: "feature/new-feature"
    variables:
      BuildConfiguration: "Release"
      RunTests: "true"
    state: run

# Run pipeline and wait for completion
- name: Run pipeline and wait
  basicPr0grammer.azure_devops.azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    wait_for_completion: true
    wait_timeout: 900
    state: run
  register: pipeline_run

# Delete a pipeline
- name: Delete pipeline
  basicPr0grammer.azure_devops.azure_devops_pipeline:
    organization_url: "https://dev.azure.com/myorg"
    project: "MyProject"
    name: "my-build-pipeline"
    state: absent
'''

RETURN = r'''
pipeline:
    description: Details of the pipeline
    returned: when state is present or run
    type: dict
    sample:
        id: 123
        name: "my-build-pipeline"
        folder: "\\Builds"
        revision: 1
        url: "https://dev.azure.com/myorg/MyProject/_apis/pipelines/123"

run:
    description: Details of the pipeline run
    returned: when state is run
    type: dict
    sample:
        id: 456
        name: "20240101.1"
        state: "completed"
        result: "succeeded"
        url: "https://dev.azure.com/myorg/MyProject/_build/results?buildId=456"

changed:
    description: Whether the module made changes
    returned: always
    type: bool
'''

import os
import time
from ansible.module_utils.basic import AnsibleModule

try:
    from azure.devops.connection import Connection
    from azure.devops.v7_1.build import models as build_models
    from azure.devops.v7_1.git import GitClient
    from msrest.authentication import BasicAuthentication
    HAS_AZURE_DEVOPS = True
except ImportError:
    HAS_AZURE_DEVOPS = False


def get_repository_id(git_client, project, repository_name):
    """Get repository ID from repository name"""
    try:
        repo = git_client.get_repository(project=project, repository_id=repository_name)
        return repo.id
    except Exception:
        return None


def get_build_definition_by_name(build_client, project, name, folder):
    """Get build definition by name and folder (path)"""
    try:
        definitions = build_client.get_definitions(project=project, name=name, path=folder)
        if definitions:
            return definitions[0]
        return None
    except Exception:
        return None


def map_repository_type(repository_type):
    """Map repository type to Azure DevOps build repository type"""
    type_map = {
        "azureReposGit": "TfsGit",
        "tfsgit": "TfsGit",
        "github": "GitHub",
        "gitHub": "GitHub",
        "tfsversioncontrol": "TfsVersionControl"
    }
    return type_map.get(repository_type, repository_type)


def create_build_definition(module, build_client, task_agent_client, git_client, project, name, folder, 
                            repository_id, repository_name, repository_type, yaml_path, default_branch):
    """Create a new build definition (pipeline)"""
    
    # Get repository ID if name was provided
    if repository_name and not repository_id:
        repository_id = get_repository_id(git_client, project, repository_name)
        if not repository_id:
            module.fail_json(msg=f"Repository '{repository_name}' not found")
    
    if not repository_id:
        module.fail_json(msg="Either repository_id or repository_name is required to create a pipeline")
    
    if not yaml_path:
        module.fail_json(msg="yaml_path is required to create a pipeline")
    
    # Normalize branch name to full ref format
    if default_branch and not default_branch.startswith("refs/"):
        default_branch = f"refs/heads/{default_branch}"
    
    # Create repository configuration
    repo = build_models.BuildRepository()
    repo.id = repository_id
    repo.type = map_repository_type(repository_type)
    repo.default_branch = default_branch
    
    # Create YAML process configuration
    # Type 2 = YAML process
    yaml_process = {
        "yamlFilename": yaml_path,
        "type": 2
    }
    
    # Create build definition
    build_def = build_models.BuildDefinition()
    build_def.name = name
    build_def.path = folder
    build_def.repository = repo
    build_def.process = yaml_process
    build_def.type = "build"
    
    # CRITICAL: Set the queue - this is required for YAML pipelines to run
    # Get the Azure Pipelines hosted queue
    try:
        queues = task_agent_client.get_agent_queues(project)
        azure_pipelines_queue = None
        for q in queues:
            if q.name == "Azure Pipelines":
                azure_pipelines_queue = q
                break
        
        if azure_pipelines_queue:
            # Create AgentPoolQueue object
            queue_obj = build_models.AgentPoolQueue()
            queue_obj.id = azure_pipelines_queue.id
            queue_obj.name = azure_pipelines_queue.name
            build_def.queue = queue_obj
    except Exception as e:
        # Queue is critical - fail if we can"t set it
        module.fail_json(msg=f"Failed to get agent queue: {str(e)}")
    
    try:
        definition = build_client.create_definition(build_def, project)
        return definition, True
    except Exception as e:
        module.fail_json(msg=f"Failed to create pipeline: {str(e)}")


def update_build_definition(module, build_client, definition, folder):
    """Update build definition (currently only folder updates are supported)"""
    changed = False
    
    # Check if folder changed
    if definition.path != folder:
        # Note: Updating path requires careful handling
        module.warn(f"Pipeline path differs (current: '{definition.path}', desired: '{folder}'). " +
                   "Path updates require careful handling and are not supported by this module.")
    
    return definition, changed


def delete_build_definition(module, build_client, project, definition_id):
    """Delete a build definition"""
    try:
        build_client.delete_definition(project, definition_id)
        return True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete pipeline: {str(e)}")


def queue_build(module, build_client, project, definition_id, branch, variables, 
               template_parameters, wait_for_completion, wait_timeout):
    """Queue a build (run a pipeline)"""
    
    # Get the full definition first to ensure we have all necessary configuration
    try:
        definition = build_client.get_definition(project, definition_id)
    except Exception as e:
        module.fail_json(msg=f"Failed to get pipeline definition: {str(e)}")
    
    # Create build object with minimal required fields
    build = build_models.Build()
    build.definition = build_models.DefinitionReference()
    build.definition.id = definition_id
    
    # Don"t set queue - let it come from the definition automatically
    # Setting it explicitly might cause validation issues
    
    # Only set branch if explicitly specified by user
    if branch:
        ref_name = branch if branch.startswith("refs/") else f"refs/heads/{branch}"
        build.source_branch = ref_name
    
    # Set template parameters if specified (for YAML pipeline parameters)
    # Template parameters must be set as a dictionary, not JSON string
    if template_parameters:
        build.template_parameters = template_parameters
    
    # Set variables if specified (runtime variables via parameters field)
    # Variables are passed as JSON string in the parameters field
    if variables:
        import json
        build.parameters = json.dumps(variables)
    
    try:
        queued_build = build_client.queue_build(build, project)
        
        # Wait for completion if requested
        if wait_for_completion:
            queued_build = wait_for_build_completion(build_client, project, queued_build.id, wait_timeout)
        
        return queued_build, True
    except Exception as e:
        module.fail_json(msg=f"Failed to run pipeline: {str(e)}")


def wait_for_build_completion(build_client, project, build_id, timeout):
    """Wait for a build to complete"""
    start_time = time.time()
    
    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            raise Exception(f"Build timed out after {timeout} seconds")
        
        # Get build status
        build = build_client.get_build(project, build_id)
        
        # Check if completed
        if build.status in ["completed", "cancelling", "postponed", "notStarted"]:
            return build
        
        # Wait before checking again
        time.sleep(5)


def build_definition_to_dict(definition):
    """Convert build definition object to dictionary"""
    if not definition:
        return None
    
    return {
        "id": definition.id,
        "name": definition.name,
        "folder": definition.path,  # path is used for folder in Build API
        "revision": definition.revision,
        "url": definition.url
    }


def build_to_dict(build):
    """Convert build object to dictionary"""
    if not build:
        return None
    
    result = {
        "id": build.id,
        "name": build.build_number,
        "state": build.status,
        "url": build.url if hasattr(build, "url") else None
    }
    
    # Add result if available
    if hasattr(build, "result") and build.result:
        result["result"] = build.result
    
    # Add created date if available  
    if hasattr(build, "start_time") and build.start_time:
        result["created_date"] = str(build.start_time)
    
    # Add finished date if available
    if hasattr(build, "finish_time") and build.finish_time:
        result["finished_date"] = str(build.finish_time)
    
    return result


def main():
    module = AnsibleModule(
        argument_spec=dict(
            organization_url=dict(type="str", required=True),
            personal_access_token=dict(type="str", required=False, no_log=True),
            project=dict(type="str", required=True),
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent", "run"]),
            folder=dict(type="str", default="\\"),
            repository_id=dict(type="str", required=False),
            repository_name=dict(type="str", required=False),
            repository_type=dict(type="str", default="azureReposGit", 
                               choices=["azureReposGit", "github", "gitHub", "tfsgit", "tfsversioncontrol"]),
            yaml_path=dict(type="str", required=False),
            default_branch=dict(type="str", default="main"),
            branch=dict(type="str", required=False),
            variables=dict(type="dict", required=False),
            template_parameters=dict(type="dict", required=False),
            wait_for_completion=dict(type="bool", default=False),
            wait_timeout=dict(type="int", default=600),
        ),
        required_if=[
            ["state", "present", ["repository_id", "repository_name", "yaml_path"], True],
        ],
        supports_check_mode=False,
    )

    if not HAS_AZURE_DEVOPS:
        module.fail_json(msg="The azure-devops Python package is required")

    organization_url = module.params["organization_url"]
    pat = module.params["personal_access_token"] or os.environ.get("AZURE_DEVOPS_PAT")
    project = module.params["project"]
    name = module.params["name"]
    state = module.params["state"]
    folder = module.params["folder"]
    repository_id = module.params["repository_id"]
    repository_name = module.params["repository_name"]
    repository_type = module.params["repository_type"]
    yaml_path = module.params["yaml_path"]
    default_branch = module.params["default_branch"]
    branch = module.params["branch"]
    variables = module.params["variables"]
    template_parameters = module.params["template_parameters"]
    wait_for_completion = module.params["wait_for_completion"]
    wait_timeout = module.params["wait_timeout"]

    if not pat:
        module.fail_json(msg="personal_access_token or AZURE_DEVOPS_PAT environment variable is required")

    # Create connection
    credentials = BasicAuthentication("", pat)
    connection = Connection(base_url=organization_url, creds=credentials)
    build_client = connection.clients.get_build_client()
    task_agent_client = connection.clients.get_task_agent_client()
    git_client = connection.clients.get_git_client()

    # Get existing build definition (pipeline)
    existing_definition = get_build_definition_by_name(build_client, project, name, folder)

    result = {
        "changed": False,
        "pipeline": None,
        "run": None
    }

    if state == "present":
        if existing_definition:
            # Update existing pipeline
            definition, changed = update_build_definition(module, build_client, existing_definition, folder)
            result["pipeline"] = build_definition_to_dict(definition)
            result["changed"] = changed
        else:
            # Create new pipeline
            definition, changed = create_build_definition(
                module, build_client, task_agent_client, git_client, project, name, folder,
                repository_id, repository_name, repository_type, yaml_path, default_branch
            )
            result["pipeline"] = build_definition_to_dict(definition)
            result["changed"] = changed

    elif state == "absent":
        if existing_definition:
            delete_build_definition(module, build_client, project, existing_definition.id)
            result["changed"] = True
        # If pipeline doesn"t exist, no change needed

    elif state == "run":
        if not existing_definition:
            module.fail_json(msg=f"Pipeline '{name}' not found in folder '{folder}'")
        
        build, changed = queue_build(
            module, build_client, project, existing_definition.id, branch,
            variables, template_parameters, wait_for_completion, wait_timeout
        )
        result["pipeline"] = build_definition_to_dict(existing_definition)
        result["run"] = build_to_dict(build)
        result["changed"] = changed

    module.exit_json(**result)


if __name__ == "__main__":
    main()
