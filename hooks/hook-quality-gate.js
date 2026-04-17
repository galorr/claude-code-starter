#!/usr/bin/env node
// Quality Gate - PreToolUse hook
// Blocks git push if ESLint errors exist in changed files.
// Prompts the user in the console to bypass or abort.
//
// How blocking works:
//   exit(0)  → allow the push to proceed
//   exit(2)  → block the push, show `reason` to the user in the console

const fs = require('fs');
const path = require('path');
const { execSync, spawnSync } = require('child_process');
const readline = require('readline');

const stdinTimeout = setTimeout(() => process.exit(0), 5000);
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || '';
    const toolInput = data.tool_input || {};

    // Only fire on Bash tool
    if (toolName !== 'Bash') process.exit(0);

    // Only fire on git push commands
    const command = toolInput.command || '';
    if (!/git\s+push/.test(command)) process.exit(0);

    // Find git root
    let gitRoot = null;
    try {
      gitRoot = execSync('git rev-parse --show-toplevel 2>/dev/null', { timeout: 5000 })
        .toString().trim();
    } catch {
      process.exit(0);
    }
    if (!gitRoot) process.exit(0);

    // Get changed JS/TS files vs origin (committed but not yet pushed)
    let changedFiles = [];
    try {
      // Files changed in commits not yet pushed
      const unpushed = execSync(
        'git diff --name-only @{u}...HEAD 2>/dev/null || git diff --name-only HEAD~1...HEAD 2>/dev/null',
        { cwd: gitRoot, timeout: 5000 }
      ).toString().trim();
      changedFiles = unpushed.split('\n').filter(f =>
        f && /\.(js|ts|tsx|jsx)$/.test(f) && fs.existsSync(path.join(gitRoot, f))
      );
    } catch {
      process.exit(0);
    }

    if (changedFiles.length === 0) process.exit(0);

    // Find ESLint (local preferred)
    const localEslint = path.join(gitRoot, 'node_modules', '.bin', 'eslint');
    const eslintCmd = fs.existsSync(localEslint) ? localEslint : null;
    if (!eslintCmd) process.exit(0); // No eslint available, don't block

    // Run ESLint
    let lintOutput = '';
    let hasErrors = false;
    try {
      const result = spawnSync(
        eslintCmd,
        ['--max-warnings=0', '--format=compact', ...changedFiles],
        { cwd: gitRoot, timeout: 30000, encoding: 'utf8' }
      );
      if (result.status !== 0) {
        hasErrors = true;
        lintOutput = (result.stdout || result.stderr || '').slice(0, 2000);
      }
    } catch {
      process.exit(0);
    }

    if (!hasErrors) process.exit(0);

    // Prompt the user interactively in the terminal
    // Write directly to /dev/tty so it appears in the console regardless of stdin/stdout piping
    let bypass = false;
    try {
      const tty = fs.openSync('/dev/tty', 'r+');
      const ttyWrite = (msg) => fs.writeSync(tty, msg);

      ttyWrite('\n');
      ttyWrite('╔══════════════════════════════════════════════════════════╗\n');
      ttyWrite('║  🚫  QUALITY GATE FAILED — ESLint errors detected        ║\n');
      ttyWrite('╚══════════════════════════════════════════════════════════╝\n');
      ttyWrite('\n' + lintOutput + '\n');
      ttyWrite('──────────────────────────────────────────────────────────\n');
      ttyWrite('Push blocked. Do you want to bypass and push anyway?\n');
      ttyWrite('  [y] Yes, push anyway (not recommended)\n');
      ttyWrite('  [n] No, fix errors first (recommended)\n');
      ttyWrite('\nYour choice [y/N]: ');

      // Read one character from /dev/tty
      const buf = Buffer.alloc(3);
      const bytesRead = fs.readSync(tty, buf, 0, 3, null);
      const answer = buf.slice(0, bytesRead).toString().trim().toLowerCase();
      bypass = answer === 'y' || answer === 'yes';

      if (bypass) {
        ttyWrite('\n⚠️  Bypassing quality gate. Push will proceed.\n\n');
      } else {
        ttyWrite('\n✅ Push cancelled. Fix the lint errors and try again.\n\n');
      }
      fs.closeSync(tty);
    } catch {
      // Can't open tty (e.g. in CI) — block by default
      bypass = false;
    }

    if (bypass) {
      process.exit(0); // Allow push
    } else {
      // exit(2) blocks the tool call and shows `reason` to the agent
      const out = JSON.stringify({
        reason: `Quality gate blocked the push. ESLint errors in changed files:\n${lintOutput}\n\nFix the errors and try pushing again, or the user can bypass by running git push manually.`,
      });
      process.stdout.write(out);
      process.exit(2);
    }
  } catch {
    process.exit(0); // Never block on unexpected errors
  }
});
