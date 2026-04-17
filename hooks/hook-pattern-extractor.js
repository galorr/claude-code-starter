#!/usr/bin/env node
// Pattern Extractor - Stop hook
// At session end, appends reusable patterns and lessons learned to
// ~/.claude/memory-bank/lessons-learned.md
//
// Only fires when:
// - Inside a git repo (so we know the project context)
// - There are modified files OR a session summary from precompact
//
// What it captures:
// - Project name (from git remote or directory name)
// - Files touched this session
// - Session summary (if precompact ran and saved state)

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

const MEMORY_BANK_DIR = path.join(os.homedir(), '.claude', 'memory-bank');
const LESSONS_FILE = path.join(MEMORY_BANK_DIR, 'lessons-learned.md');

const stdinTimeout = setTimeout(() => process.exit(0), 3000);
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    const sessionId = data.session_id;
    const cwd = process.env.PWD || process.cwd();

    // Only run in a git repo
    let gitRoot = null;
    try {
      gitRoot = execSync('git rev-parse --show-toplevel 2>/dev/null', {
        cwd,
        timeout: 3000,
      }).toString().trim();
    } catch {
      process.exit(0);
    }
    if (!gitRoot) process.exit(0);

    // Read precompact state if available (has the session summary)
    let summary = '';
    if (sessionId) {
      const statePath = path.join(os.tmpdir(), `claude-precompact-${sessionId}.json`);
      if (fs.existsSync(statePath)) {
        try {
          const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
          summary = state.summary || '';
        } catch { /* ignore */ }
      }
    }

    // Get files modified this session from git
    let modifiedFiles = [];
    try {
      const diff = execSync('git diff --name-only HEAD 2>/dev/null', {
        cwd: gitRoot,
        timeout: 5000,
      }).toString().trim();
      modifiedFiles = diff.split('\n').filter(Boolean);
    } catch { /* ignore */ }

    // Only append if there's meaningful data
    if (!summary && modifiedFiles.length === 0) process.exit(0);

    // Get project name from git remote or directory name
    let projectName = path.basename(gitRoot);
    try {
      const remote = execSync('git remote get-url origin 2>/dev/null', {
        cwd: gitRoot,
        timeout: 3000,
      }).toString().trim();
      // Extract repo name from URL: https://github.com/org/repo.git or git@github.com:org/repo.git
      const match = remote.match(/[/:]([^/:]+?)(?:\.git)?$/);
      if (match) projectName = match[1];
    } catch { /* use dirname fallback */ }

    // Ensure memory-bank directory exists
    if (!fs.existsSync(MEMORY_BANK_DIR)) {
      fs.mkdirSync(MEMORY_BANK_DIR, { recursive: true });
    }

    // Build the entry
    const date = new Date().toISOString().split('T')[0];
    const filesList = modifiedFiles.length > 0
      ? `\n- **Files touched:** ${modifiedFiles.slice(0, 10).join(', ')}${modifiedFiles.length > 10 ? ` (+${modifiedFiles.length - 10} more)` : ''}`
      : '';
    const summarySection = summary
      ? `\n- **Notes:** ${summary.slice(0, 600)}`
      : '';

    const entry = [
      `\n## ${date} — ${projectName}`,
      filesList,
      summarySection,
      '',
    ].join('\n');

    // Append to lessons-learned.md, creating it with a header if new
    if (!fs.existsSync(LESSONS_FILE)) {
      fs.writeFileSync(LESSONS_FILE, [
        '# Lessons Learned',
        '',
        'Auto-populated by the pattern extractor hook at session end.',
        'Each entry captures files touched and session notes per project.',
        'Review periodically and promote recurring patterns to dedicated skill files.',
        '',
      ].join('\n'));
    }

    fs.appendFileSync(LESSONS_FILE, entry);
    process.exit(0);
  } catch {
    process.exit(0);
  }
});
