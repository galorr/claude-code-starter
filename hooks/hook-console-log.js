#!/usr/bin/env node
// Console.log Detector - PostToolUse hook
// Warns the agent when console.log/console.debug/console.warn statements
// are detected in code files after Write/Edit.
// Excludes test files and intentional logger patterns.

const fs = require('fs');
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

    if (!['Write', 'Edit'].includes(toolName)) process.exit(0);

    const filePath = toolInput.file_path || '';

    // Only check source code files
    if (!/\.(js|ts|tsx|jsx)$/.test(filePath)) process.exit(0);

    // Skip test files
    if (/\.(spec|test)\.(js|ts|tsx|jsx)$/.test(filePath)) process.exit(0);
    if (/\/__tests__\//.test(filePath)) process.exit(0);

    if (!fs.existsSync(filePath)) process.exit(0);

    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split('\n');

    const hits = [];
    lines.forEach((line, idx) => {
      // Match console.log/debug/warn but not console.error (those may be intentional)
      // Also skip lines that are commented out
      const trimmed = line.trim();
      if (trimmed.startsWith('//') || trimmed.startsWith('*')) return;
      if (/console\.(log|debug|warn)\s*\(/.test(line)) {
        hits.push(`  Line ${idx + 1}: ${trimmed.slice(0, 100)}`);
      }
    });

    if (hits.length === 0) process.exit(0);

    const result = {
      additionalContext: `⚠️  Debug statements detected in ${path.basename(filePath)}:\n${hits.join('\n')}\n\nRemove console.log/debug/warn before committing. Use a proper logger or delete them.`,
    };
    process.stdout.write(JSON.stringify(result));
    process.exit(0);
  } catch {
    process.exit(0);
  }
});
