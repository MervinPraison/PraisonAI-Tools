#!/usr/bin/env node
/**
 * Run: node .github/scripts/release-gate-selftest.js
 */
const rg = require('./release-gate.js');
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

assert(`package name is ${config.pypiPackageName}`, config.pypiPackageName === 'praisonai-tools');
assert('bumpPatch works', rg.bumpPatch('0.3.127') === '0.3.128');

try {
  const versions = rg.readVersionsFromTree(process.cwd());
  assert('reads current version', /^\d+\.\d+\.\d+$/.test(versions.current));
  assert('computes target patch', versions.target === rg.bumpPatch(versions.current));
} catch (err) {
  console.error('FAIL: readVersionsFromTree', err.message);
  failed += 1;
}

assert('PACKAGE_PATHS includes pyproject', rg.PACKAGE_PATHS.includes('pyproject.toml'));

(async () => {
  const noonUtc = new Date('2026-07-08T12:00:00Z');
  const mockGithub = {
    rest: {
      actions: {
        listWorkflowRuns: async () => ({
          data: {
            workflow_runs: [
              {
                conclusion: 'success',
                created_at: '2026-07-08T09:00:00Z',
                status: 'completed',
              },
            ],
          },
        }),
      },
    },
  };

  assert('PATCH_RELEASE_INTERVAL_DAYS is 3', rg.PATCH_RELEASE_INTERVAL_DAYS === 3);
  assert(
    'hasSuccessfulReleaseWithinDays blocks recent release',
    await rg.hasSuccessfulReleaseWithinDays(mockGithub, 'o', 'r', noonUtc)
  );

  const oldReleaseGithub = {
    rest: {
      actions: {
        listWorkflowRuns: async () => ({
          data: {
            workflow_runs: [
              {
                conclusion: 'success',
                created_at: '2026-07-04T09:00:00Z',
                status: 'completed',
              },
            ],
          },
        }),
      },
    },
  };
  assert(
    'hasSuccessfulReleaseWithinDays allows after 3 days',
    !(await rg.hasSuccessfulReleaseWithinDays(oldReleaseGithub, 'o', 'r', noonUtc))
  );

  process.exit(failed ? 1 : 0);
})();
