/**
 * Load per-repo gate configuration (installed as .github/scripts/gate-config.js).
 */
function loadGateConfig() {
  try {
    return require('./gate-config.js');
  } catch (err) {
    if (err.code !== 'MODULE_NOT_FOUND') throw err;
    throw new Error(
      'Missing .github/scripts/gate-config.js — run install.sh from github-automation-template'
    );
  }
}

module.exports = { loadGateConfig };
