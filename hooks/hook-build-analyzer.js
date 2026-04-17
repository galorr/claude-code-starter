#!/usr/bin/env node
// Build Error Analyzer - PostToolUse hook (async)
// Analyzes build command output and surfaces structured error summaries.
// Fires after Bash tool on build-like commands. Runs async to avoid blocking.

const path = require('path');

const stdinTimeout = setTimeout(() => process.exit(0), 3000);
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || '';
    const toolInput = data.tool_input || {};
    const toolResult = data.tool_response || data.output || '';

    // Only fire on Bash tool
    if (toolName !== 'Bash') process.exit(0);

    // Only fire on build-like commands
    const command = toolInput.command || '';
    const isBuildCmd = /\b(build|compile|tsc|ng build|next build|webpack|vite build|gradle|mvn|cargo build|go build)\b/.test(command);
    if (!isBuildCmd) process.exit(0);

    // Only analyze if there was output (tool result)
    const output = typeof toolResult === 'string' ? toolResult : JSON.stringify(toolResult);
    if (!output || output.length < 10) process.exit(0);

    // Check if build succeeded
    const succeeded = /successfully|compiled successfully|build complete|done in/i.test(output);
    if (succeeded) process.exit(0);

    // Extract error lines
    const lines = output.split('\n');
    const errorLines = lines.filter(l =>
      /error(\s|:)|ERROR|failed|FAILED|Cannot find|Module not found|Type error/i.test(l)
    ).slice(0, 15);

    if (errorLines.length === 0) process.exit(0);

    const summary = errorLines.join('\n').slice(0, 1500);
    const result = {
      additionalContext: `🔴 Build errors detected:\n\`\`\`\n${summary}\n\`\`\`\nAddress these build errors before proceeding.`,
    };
    process.stdout.write(JSON.stringify(result));
    process.exit(0);
  } catch {
    process.exit(0);
  }
});
