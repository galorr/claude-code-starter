---
name: n8n-builder
description: Design, build, validate, and deploy n8n automation workflows using n8n-MCP tools. Use this skill whenever the user wants to create or modify an n8n workflow, automate a process with n8n, connect n8n nodes, or asks about n8n triggers, actions, or integrations. Trigger on "build an n8n workflow", "automate this with n8n", "create an n8n automation", or any mention of n8n nodes, webhooks, or workflow automation. Always validate before and after building.
---

# N8N Workflow Builder

Design, validate, and deploy n8n automation workflows with maximum accuracy.

> **Requires n8n MCP server to be configured.** All `tools_documentation()`, `search_nodes()`, `validate_workflow()` etc. calls are n8n MCP tools.

## Core Process (Always Follow This Order)

### 1. Read Documentation First
```
tools_documentation()
```
Always start here to understand current best practices and tool availability.

### 2. Discovery — Find the Right Nodes
```
search_nodes({query: 'keyword'})          # Search by functionality
list_nodes({category: 'trigger'})         # Browse by category
list_ai_tools()                           # See AI-capable nodes
```

### 3. Configure — Get Node Details
```
get_node_essentials(nodeType)             # Start here — only 10-20 key properties
search_node_properties(nodeType, 'auth')  # Find specific properties
get_node_for_task('send_email')           # Pre-configured templates
get_node_documentation(nodeType)          # Full docs when needed
```

### 4. Pre-Validate — Before Building
```
validate_node_minimal(nodeType, config)           # Quick required fields check
validate_node_operation(nodeType, config, profile) # Full operation-aware validation
```
**Fix all validation errors before writing workflow JSON.**

### 5. Build the Workflow
- Use validated configurations only
- Connect nodes with proper structure
- Add error handling where appropriate
- Use n8n expressions: `$json`, `$node["NodeName"].json`, `$('NodeName').item.json`
- Produce workflow as artifact (unless user asks to deploy to instance)

### 6. Validate the Complete Workflow
```
validate_workflow(workflow)              # Full validation
validate_workflow_connections(workflow) # Structure + AI tool connections
validate_workflow_expressions(workflow) # All expression syntax
```
Fix any issues. Never deploy an unvalidated workflow.

### 7. Deploy (If n8n API Configured)
```
n8n_create_workflow(workflow)
n8n_validate_workflow({id: 'workflow-id'})  # Post-deployment check
```

### 8. Update Existing Workflows (Prefer Diffs — 80-90% Token Savings)
```
n8n_update_partial_workflow({
  workflowId: id,
  operations: [
    {type: 'updateNode', nodeId: 'slack1', changes: {position: [100, 200]}},
    {type: 'addNode', node: {...}},
    {type: 'deleteNode', nodeId: 'old-node'},
    {type: 'addConnection', connection: {...}}
  ]
})
```

## Key Insights

- **ANY node can be an AI tool** — not just those with `usableAsTool: true`
- **Pre-validate configurations** before building saves time
- **Post-validate workflows** always, before deployment
- **Use diff updates** for existing workflows (not full replace)
- **Short, specific queries** work best for `search_nodes` (1-4 words)

## Workflow JSON Structure

```json
{
  "name": "My Workflow",
  "nodes": [
    {
      "id": "uuid",
      "name": "NodeName",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2,
      "position": [250, 300],
      "parameters": {}
    }
  ],
  "connections": {
    "Trigger": {
      "main": [[{"node": "NextNode", "type": "main", "index": 0}]]
    }
  },
  "active": false
}
```

## Common Patterns

### Webhook Trigger → Process → Notify
```
Webhook Trigger → Function/Code Node → Slack/Email Notification
```

### Scheduled Data Sync
```
Cron Trigger → HTTP Request (source) → Transform → HTTP Request (destination)
```

### AI-Powered Processing
```
Trigger → Retrieve Data → AI Agent (with tools) → Store Result
```

## MCP Server Integration
For external services, include in API call:
```javascript
mcp_servers: [{
  type: "url",
  url: "https://mcp.service.com/sse",
  name: "service-mcp"
}]
```

## Response Structure
1. **Discovery** — available nodes and options
2. **Pre-Validation** — validate configs before building
3. **Workflow Build** — produce validated workflow JSON/artifact
4. **Workflow Validation** — run all validation tools
5. **Deploy** — only after all validations pass
6. **Post-Validation** — confirm deployment success
