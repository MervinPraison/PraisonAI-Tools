/**
 * PraisonAI-Tools gate configuration.
 */

module.exports = {
  repoFullName: 'MervinPraison/PraisonAI-Tools',
  productPathPrefixes: ['praisonai_tools/', 'tests/'],
  // Workflows stay gated; pyproject.toml is normal for optional tool deps.
  sensitivePathPatterns: [
    /^\.github\/workflows\//,
  ],
  // Tool + tests + docs routinely exceed the UI/SDK 800-line default.
  maxAutoAdditions: 2000,
  maxAutoFiles: 30, // same as the previous hard-coded default; configurable for future tuning
  requiredCheckPatterns: [/^ci$/i, /python/i, /test/i, /lint/i, /ruff/i],
  ciWorkflowFile: 'ci.yml',
  ciWorkflowName: 'CI',
  mergeGateWorkflowRuns: ['CI', 'Claude Assistant'],
  ciFailureWorkflowRuns: ['CI'],
  pypiPackageName: 'praisonai-tools',
  packagePaths: ['praisonai_tools', 'pyproject.toml'],
  finalClaudeScope:
    'SCOPE: Focus ONLY on PraisonAI-Tools (praisonai_tools/, tests). '
    + 'Agent-callable integrations belong here, not praisonaiagents core or PraisonAI-Plugins.',
  finalClaudeProductValue:
    '4. Product value: tools must be agent-invokable via parameters; lazy imports; '
    + 'no lifecycle hooks or sandbox backends in this repo.',
  agentPyChecks: false,
  reviewBotLogins: [
    'coderabbitai[bot]',
    'qodo-code-review[bot]',
    'greptile-apps[bot]',
  ],
};
