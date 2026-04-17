#!/usr/bin/env node
// TypeScript Type Checker - PostToolUse hook
// Runs tsc --noEmit after Write/Edit on .ts/.tsx files
// Only fires if a tsconfig.json exists in the project root

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

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

    // Only fire on Write or Edit tools
    if (!['Write', 'Edit'].includes(toolName)) process.exit(0);

    // Only fire on .ts or .tsx files
    const filePath = toolInput.file_path || '';
    if (!/\.(ts|tsx)$/.test(filePath)) process.exit(0);

    // Find project root by walking up from file to find tsconfig.json
    let dir = path.dirname(filePath);
    let tsconfigPath = null;
    for (let i = 0; i < 10; i++) {
      const candidate = path.join(dir, 'tsconfig.json');
      if (fs.existsSync(candidate)) {
        tsconfigPath = candidate;
        break;
      }
      const parent = path.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }

    if (!tsconfigPath) process.exit(0);

    const projectRoot = path.dirname(tsconfigPath);

    try {
      execSync('npx tsc --noEmit --skipLibCheck 2>&1', {
        cwd: projectRoot,
        timeout: 30000,
        stdio: 'pipe',
      });
      // No errors — exit silently
      process.exit(0);
    } catch (err) {
      const output = err.stdout ? err.stdout.toString() : err.message;
      // Surface type errors as additionalContext to the agent
      const errors = output.slice(0, 2000); // cap length
      const result = {
        additionalContext: `TypeScript type errors detected after file save:\n\`\`\`\n${errors}\n\`\`\`\nFix these type errors before proceeding.`,
      };
      process.stdout.write(JSON.stringify(result));
      process.exit(0);
    }
  } catch {
    process.exit(0);
  }
});
