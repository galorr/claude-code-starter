#!/usr/bin/env node
// PreCompact State Saver - PreCompact hook
// Saves current task state to a temp file before context compression.
// The state is written to /tmp/claude-precompact-{session_id}.json
// and can be read by SessionStart or the agent on resumption.

const fs = require('fs');
const os = require('os');
const path = require('path');

const stdinTimeout = setTimeout(() => process.exit(0), 3000);
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    const sessionId = data.session_id;
    if (!sessionId) process.exit(0);

    const summary = data.summary || data.compact_summary || '';
    const cwd = process.env.PWD || process.cwd();

    const state = {
      timestamp: Date.now(),
      session_id: sessionId,
      cwd,
      summary: summary.slice(0, 3000),
      saved_at: new Date().toISOString(),
    };

    const outPath = path.join(os.tmpdir(), `claude-precompact-${sessionId}.json`);
    fs.writeFileSync(outPath, JSON.stringify(state, null, 2));

    // Also write a human-readable breadcrumb to the project root if in a git repo
    try {
      const { execSync } = require('child_process');
      const gitRoot = execSync('git rev-parse --show-toplevel 2>/dev/null', {
        cwd,
        timeout: 3000,
      }).toString().trim();

      if (gitRoot) {
        const breadcrumb = path.join(gitRoot, '.claude-session-state.json');
        fs.writeFileSync(breadcrumb, JSON.stringify(state, null, 2));
      }
    } catch {
      // Not a git repo — tmp file is enough
    }

    process.exit(0);
  } catch {
    process.exit(0);
  }
});
