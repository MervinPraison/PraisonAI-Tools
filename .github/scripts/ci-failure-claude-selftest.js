#!/usr/bin/env node
/**
 * Run: node .github/scripts/ci-failure-claude-selftest.js
 */
const ciFix = require('./ci-failure-claude.js');
const mergeGate = require('./merge-gate.js');
const config = require('./gate-config.js');

let failed = 0;
function assert(name, cond) {
  if (!cond) {
    console.error('FAIL:', name);
    failed += 1;
  } else {
    console.log('ok:', name);
  }
}

const LOG = `
python	UNKNOWN STEP	FAILED (0.0100s) tests/unit/test_example.py::test_foo - AssertionError: bar
python	UNKNOWN STEP	##[error]Process completed with exit code 1.
`;

const parsed = ciFix.parsePytestFailures(LOG);
assert('parses pytest failure', parsed.length === 1);
assert('uses CI workflow list', config.ciFailureWorkflowRuns.includes('CI'));

const comment = ciFix.buildCiFixComment({
  headSha: 'abc1234567890abcdef1234567890abcdef12',
  failedChecks: [{ name: 'python', workflow: 'CI', html_url: 'https://example.com/job/1' }],
  failureSummaries: [{ jobName: 'python', failures: parsed }],
});
assert('comment mentions product guardrails', comment.includes('Product guardrails'));

process.exit(failed ? 1 : 0);
