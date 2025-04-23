# Plan Versioning System

The Plan Versioning System is a powerful feature in Nexagent that allows you to create, manage, and version plans for complex tasks. This system provides functionality similar to version control systems like Git, but specifically designed for task planning.

## Key Features

- **Plan Creation and Management**: Create, update, and delete plans
- **Version Control**: Create versions of plans to track changes over time
- **Version Comparison**: Compare different versions to see what has changed
- **Rollback Capability**: Roll back to previous versions if needed
- **Version History**: View the history of changes to a plan
- **Version Tagging**: Tag important versions for easy reference

## Using the Plan Versioning System

The Plan Versioning System is accessible through the CLI interface using the `plan` command.

### Basic Commands

- `plan help` - Show help for the plan command
- `plan list` - List all plans
- `plan create <plan_id> <title>` - Create a new plan
- `plan get <plan_id>` - Get a plan
- `plan update <plan_id> <title>` - Update a plan

### Version Management Commands

- `plan version create <plan_id> <version_id> <description>` - Create a version
- `plan version list <plan_id>` - List versions of a plan
- `plan version get <plan_id> <version_id>` - Get a specific version
- `plan version compare <plan_id> <version_id1> <version_id2>` - Compare versions
- `plan version rollback <plan_id> <version_id>` - Rollback to a version
- `plan version history <plan_id>` - Get version history

## Example Workflow

Here's an example workflow for using the Plan Versioning System:

1. Create a new plan:
   ```
   plan create project1 "My Project Plan"
   ```

2. Update the plan with steps:
   ```
   plan update project1 "My Project Plan with Steps"
   ```

3. Create a version of the plan:
   ```
   plan version create project1 v1 "Initial version"
   ```

4. Make changes to the plan:
   ```
   plan update project1 "My Project Plan with Updated Steps"
   ```

5. Create another version:
   ```
   plan version create project1 v2 "Updated version"
   ```

6. Compare the versions:
   ```
   plan version compare project1 v2 v1
   ```

7. Roll back to a previous version if needed:
   ```
   plan version rollback project1 v1
   ```

## Benefits of Plan Versioning

- **Track Changes**: Keep track of how your plans evolve over time
- **Experiment Safely**: Try different approaches knowing you can always go back
- **Collaboration**: Share different versions of plans with team members
- **Documentation**: Maintain a history of planning decisions
- **Accountability**: Know who made what changes and when

## Integration with Nexagent

The Plan Versioning System is fully integrated with Nexagent's other features, allowing you to:

- Use the planning tool in agent workflows
- Reference plans in conversations
- Export plans to various formats
- Share plans with other users

## Technical Implementation

The Plan Versioning System is implemented in the `app/tools/planning.py` file and is accessible through the CLI interface in `app/cli.py`. The system uses a memory-based storage system for plans and versions, with plans stored in a dictionary by plan ID and versions stored in a nested dictionary by plan ID and version ID.
