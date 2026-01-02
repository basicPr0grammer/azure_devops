# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-02

### Added
- Initial release of the Azure DevOps Ansible Collection
- **azure_devops_repository** - Manage Git repositories
- **azure_devops_pipeline** - Manage and run CI/CD pipelines
- **azure_devops_environment** - Manage deployment environments with approvals
- **azure_devops_service_endpoint** - Manage service connections (Azure RM, GitHub, Docker, Kubernetes, Generic)
- **azure_devops_branch_policy** - Configure branch protection policies (reviewers, work item linking, comment resolution, build validation)
- **azure_devops_pipeline_approval** - Approve or reject pipeline runs
- **azure_devops_variable_group** - Manage variable groups with secrets support
- **azure_devops_work_item** - Create, update, and delete work items with full field support and parent-child linking
- **azure_devops_agent_pool** - List and monitor agent pools and agents
- **azure_devops_service_hook** - Manage webhooks for Azure DevOps events (work items, pull requests, builds, deployments)
- Integration tests for all modules
- Comprehensive documentation and examples
- Idempotency support for all operations
- Check mode support for all modules

### Features
- Full support for Azure DevOps REST API v7.1
- Environment variable authentication (AZURE_DEVOPS_PAT)
- Detailed error handling and validation
- Support for secret variables in variable groups
- Branch policy configuration with multiple policy types
- Work item parent-child linking
- Service hooks with filtering (work item types, area paths, etc.)
- Multiple webhook consumers (HTTP, Slack, Teams, Azure Service Bus)

[1.0.0]: https://github.com/basicPr0grammer/ansible-azure-devops/releases/tag/v1.0.0
