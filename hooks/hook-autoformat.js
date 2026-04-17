#!/usr/bin/env node
// Auto-Formatter - PostToolUse hook
// Runs prettier on .js/.ts/.tsx/.json files after Write/Edit
// Falls back gracefully if prettier is not installed

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

    if (!['Write', 'Edit'].includes(toolName)) process.exit(0);

    const filePath = toolInput.file_path || '';
    if (!/\.(js|ts|tsx|jsx|json)$/.test(filePath)) process.exit(0);
    if (!fs.existsSync(filePath)) process.exit(0);

    // Find project root (look for package.json)
    let dir = path.dirname(filePath);
    let projectRoot = null;
    for (let i = 0; i < 10; i++) {
      if (fs.existsSync(path.join(dir, 'package.json'))) {
        projectRoot = dir;
        break;
      }
      const parent = path.dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }

    if (!projectRoot) process.exit(0);

    // Check prettier exists (local or global)
    const localPrettier = path.join(projectRoot, 'node_modules', '.bin', 'prettier');
    const prettierCmd = fs.existsSync(localPrettier) ? localPrettier : 'prettier';

    try {
      execSync(`${prettierCmd} --write "${filePath}" 2>&1`, {
        cwd: projectRoot,
        timeout: 15000,
        stdio: 'pipe',
      });
    } catch {
      // Prettier not available or failed — exit silently, not blocking
    }

    process.exit(0);
  } catch {
    process.exit(0);
  }
});
