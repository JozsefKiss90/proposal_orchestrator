#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function main() {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!inputPath || !outputPath) {
    throw new Error('usage: node ua-arch-analyze.js <input.json> <output.json>');
  }
  const input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const fileNodes = input.fileNodes || [];
  const importEdges = input.importEdges || [];
  const allEdges = input.allEdges || [];

  const nodeById = new Map();
  for (const n of fileNodes) nodeById.set(n.id, n);
  const fileIds = new Set(nodeById.keys());

  // ---------- helpers ----------
  const norm = (p) => (p || '').replace(/\\/g, '/').replace(/^\.\//, '');

  // ---------- A. common prefix + directory grouping ----------
  const paths = fileNodes.map((n) => norm(n.filePath || n.name || n.id));
  function commonPrefixDirs(list) {
    if (list.length === 0) return '';
    let segs = list[0].split('/').slice(0, -1);
    for (const p of list.slice(1)) {
      const s = p.split('/').slice(0, -1);
      let i = 0;
      while (i < segs.length && i < s.length && segs[i] === s[i]) i++;
      segs = segs.slice(0, i);
      if (segs.length === 0) break;
    }
    return segs.length ? segs.join('/') + '/' : '';
  }
  const prefix = commonPrefixDirs(paths);

  function groupOf(node) {
    let p = norm(node.filePath || node.name || node.id);
    if (prefix && p.startsWith(prefix)) p = p.slice(prefix.length);
    const segs = p.split('/');
    if (segs.length === 1) return '(root)';
    // two-level grouping for known container dirs
    if (segs.length > 2 && (segs[0] === '.claude' || segs[0] === 'runner' || segs[0] === 'harness')) {
      return segs[0] + '/' + segs[1];
    }
    return segs[0];
  }

  const directoryGroups = {};
  const groupByNode = new Map();
  for (const n of fileNodes) {
    const g = groupOf(n);
    groupByNode.set(n.id, g);
    (directoryGroups[g] = directoryGroups[g] || []).push(n.id);
  }

  // ---------- B. node type grouping ----------
  const nodeTypeGroups = {};
  for (const n of fileNodes) {
    (nodeTypeGroups[n.type] = nodeTypeGroups[n.type] || []).push(n.id);
  }

  // ---------- C. adjacency / fan-in / fan-out ----------
  const fileFanIn = {};
  const fileFanOut = {};
  const outAdj = new Map();
  for (const e of importEdges) {
    if (!fileIds.has(e.source) || !fileIds.has(e.target)) continue;
    if (!outAdj.has(e.source)) outAdj.set(e.source, new Set());
    outAdj.get(e.source).add(e.target);
  }
  for (const [src, targets] of outAdj) {
    fileFanOut[src] = targets.size;
    for (const t of targets) fileFanIn[t] = (fileFanIn[t] || 0) + 1;
  }

  // ---------- D. cross-category dependency analysis ----------
  const crossMap = new Map();
  const nonCodeToCode = [];
  for (const e of allEdges) {
    const s = nodeById.get(e.source);
    const t = nodeById.get(e.target);
    if (!s || !t) continue;
    if (s.type === t.type && s.type === 'file') continue;
    const key = s.type + '|' + t.type + '|' + e.type;
    crossMap.set(key, (crossMap.get(key) || 0) + 1);
    if (s.type !== 'file' && t.type === 'file') {
      nonCodeToCode.push({ from: e.source, to: e.target, edgeType: e.type });
    }
  }
  const crossCategoryEdges = [...crossMap.entries()]
    .map(([k, count]) => {
      const [fromType, toType, edgeType] = k.split('|');
      return { fromType, toType, edgeType, count };
    })
    .sort((a, b) => b.count - a.count);

  // ---------- E. inter-group import frequency ----------
  const interMap = new Map();
  for (const e of importEdges) {
    const gs = groupByNode.get(e.source);
    const gt = groupByNode.get(e.target);
    if (!gs || !gt || gs === gt) continue;
    const key = gs + '|' + gt;
    interMap.set(key, (interMap.get(key) || 0) + 1);
  }
  const interGroupImports = [...interMap.entries()]
    .map(([k, count]) => {
      const [from, to] = k.split('|');
      return { from, to, count };
    })
    .sort((a, b) => b.count - a.count);

  // ---------- F. intra-group density ----------
  const intraGroupDensity = {};
  for (const g of Object.keys(directoryGroups)) {
    intraGroupDensity[g] = { internalEdges: 0, totalEdges: 0, density: 0 };
  }
  for (const e of importEdges) {
    const gs = groupByNode.get(e.source);
    const gt = groupByNode.get(e.target);
    if (!gs || !gt) continue;
    if (gs === gt) {
      intraGroupDensity[gs].internalEdges++;
      intraGroupDensity[gs].totalEdges++;
    } else {
      intraGroupDensity[gs].totalEdges++;
      intraGroupDensity[gt].totalEdges++;
    }
  }
  for (const g of Object.keys(intraGroupDensity)) {
    const d = intraGroupDensity[g];
    d.density = d.totalEdges ? +(d.internalEdges / d.totalEdges).toFixed(3) : 0;
  }

  // ---------- G. directory pattern matching ----------
  const DIR_PATTERNS = [
    [['routes', 'api', 'controllers', 'endpoints', 'handlers', 'serializers', 'routers', 'blueprints', 'controller'], 'api'],
    [['services', 'core', 'lib', 'domain', 'logic', 'signals', 'composables', 'mailers', 'jobs', 'channels', 'internal'], 'service'],
    [['models', 'db', 'data', 'persistence', 'repository', 'entities', 'entity', 'migrations', 'sql', 'database'], 'data'],
    [['components', 'views', 'pages', 'ui', 'layouts', 'screens'], 'ui'],
    [['middleware', 'plugins', 'interceptors', 'guards'], 'middleware'],
    [['utils', 'helpers', 'common', 'shared', 'tools', 'templatetags', 'pkg'], 'utility'],
    [['config', 'constants', 'env', 'settings', 'management', 'commands'], 'config'],
    [['__tests__', 'test', 'tests', 'spec', 'specs'], 'test'],
    [['types', 'interfaces', 'schemas', 'contracts', 'dtos', 'dto', 'request', 'response', 'schema'], 'types'],
    [['hooks'], 'hooks'],
    [['store', 'state', 'reducers', 'actions', 'slices'], 'state'],
    [['assets', 'static', 'public'], 'assets'],
    [['cmd', 'bin'], 'entry'],
    [['docs', 'documentation', 'wiki'], 'documentation'],
    [['deploy', 'deployment', 'infra', 'infrastructure'], 'infrastructure'],
    [['.github', '.gitlab', '.circleci'], 'ci-cd'],
    [['k8s', 'kubernetes', 'helm', 'charts', 'terraform', 'tf', 'docker'], 'infrastructure'],
  ];
  function matchDir(name) {
    const leaf = name.split('/').pop();
    for (const [names, label] of DIR_PATTERNS) {
      if (names.includes(leaf)) return label;
    }
    return null;
  }
  const patternMatches = {};
  for (const g of Object.keys(directoryGroups)) {
    patternMatches[g] = matchDir(g);
  }

  // file-level patterns
  const filePatterns = {};
  for (const n of fileNodes) {
    const p = norm(n.filePath || '');
    const base = p.split('/').pop();
    let label = null;
    if (/(\.test\.|\.spec\.)/.test(base) || /^test_.*\.py$/.test(base) || /_test\.go$/.test(base) || /Test\.java$/.test(base)) label = 'test';
    else if (base === '__main__.py' || base === 'main.py') label = 'entry';
    else if (base === '__init__.py') label = 'entry';
    else if (base === 'pyproject.toml' || base === 'setup.py' || base === 'setup.cfg') label = 'config';
    else if (/\.(md|rst)$/i.test(base)) label = 'documentation';
    else if (/\.(ya?ml)$/i.test(base)) label = 'config';
    else if (/\.json$/i.test(base)) label = 'config';
    if (label) filePatterns[n.id] = label;
  }

  // ---------- H. deployment topology ----------
  const infraFiles = [];
  let hasDockerfile = false, hasCompose = false, hasK8s = false, hasTerraform = false, hasCI = false;
  for (const p of paths) {
    const base = p.split('/').pop();
    if (/^Dockerfile/.test(base)) { hasDockerfile = true; infraFiles.push(p); }
    if (/^docker-compose/.test(base)) { hasCompose = true; infraFiles.push(p); }
    if (/\.tf(vars)?$/.test(base)) { hasTerraform = true; infraFiles.push(p); }
    if (p.includes('.github/workflows/') || base === '.gitlab-ci.yml' || base === 'Jenkinsfile') { hasCI = true; infraFiles.push(p); }
    if (p.includes('k8s/') || p.includes('kubernetes/') || p.includes('helm/')) { hasK8s = true; infraFiles.push(p); }
    if (base === 'Makefile') { infraFiles.push(p); }
  }

  // ---------- I. data pipeline detection ----------
  const dataPipeline = { schemaFiles: [], migrationFiles: [], dataModelFiles: [], apiHandlerFiles: [] };
  for (const n of fileNodes) {
    const p = norm(n.filePath || '');
    const tags = (n.tags || []).map((t) => String(t).toLowerCase());
    if (n.type === 'schema' || /schema/i.test(p) || tags.includes('schema')) dataPipeline.schemaFiles.push(p);
    if (/migration/i.test(p)) dataPipeline.migrationFiles.push(p);
    if (tags.includes('data-model') || tags.includes('model')) dataPipeline.dataModelFiles.push(p);
    if (tags.includes('api-handler') || tags.includes('cli') || tags.includes('entry-point')) dataPipeline.apiHandlerFiles.push(p);
  }

  // ---------- J. documentation coverage ----------
  const docNodes = fileNodes.filter((n) => n.type === 'document' || /\.(md|rst)$/i.test(norm(n.filePath || '')));
  const groupsWithDocs = new Set(docNodes.map((n) => groupByNode.get(n.id)));
  const totalGroups = Object.keys(directoryGroups).length;
  const docCoverage = {
    groupsWithDocs: groupsWithDocs.size,
    totalGroups,
    coverageRatio: totalGroups ? +(groupsWithDocs.size / totalGroups).toFixed(2) : 0,
    undocumentedGroups: Object.keys(directoryGroups).filter((g) => !groupsWithDocs.has(g)),
  };

  // ---------- K. dependency direction ----------
  const pairSeen = new Set();
  const dependencyDirection = [];
  for (const { from, to, count } of interGroupImports) {
    const key = [from, to].sort().join('||');
    if (pairSeen.has(key)) continue;
    pairSeen.add(key);
    const reverse = interMap.get(to + '|' + from) || 0;
    if (count > reverse) dependencyDirection.push({ dependent: from, dependsOn: to, forward: count, reverse });
    else if (reverse > count) dependencyDirection.push({ dependent: to, dependsOn: from, forward: reverse, reverse: count });
    else dependencyDirection.push({ dependent: from, dependsOn: to, forward: count, reverse, bidirectional: true });
  }

  // ---------- extras: group-level in/out sets ----------
  const groupImportsFrom = {};
  const groupImportedBy = {};
  for (const { from, to } of interGroupImports) {
    (groupImportsFrom[from] = groupImportsFrom[from] || []).push(to);
    (groupImportedBy[to] = groupImportedBy[to] || []).push(from);
  }

  // top hubs
  const topFanIn = Object.entries(fileFanIn).sort((a, b) => b[1] - a[1]).slice(0, 25);
  const topFanOut = Object.entries(fileFanOut).sort((a, b) => b[1] - a[1]).slice(0, 25);

  const filesPerGroup = {};
  for (const [g, ids] of Object.entries(directoryGroups)) filesPerGroup[g] = ids.length;
  const nodeTypeCounts = {};
  for (const [t, ids] of Object.entries(nodeTypeGroups)) nodeTypeCounts[t] = ids.length;

  const results = {
    scriptCompleted: true,
    commonPrefix: prefix,
    directoryGroups,
    nodeTypeGroups,
    crossCategoryEdges,
    nonCodeToCodeSample: nonCodeToCode.slice(0, 60),
    interGroupImports,
    intraGroupDensity,
    patternMatches,
    filePatterns,
    deploymentTopology: {
      hasDockerfile, hasCompose, hasK8s, hasTerraform, hasCI,
      infraFiles: [...new Set(infraFiles)],
    },
    dataPipeline: {
      schemaFiles: [...new Set(dataPipeline.schemaFiles)],
      migrationFiles: [...new Set(dataPipeline.migrationFiles)],
      dataModelFiles: [...new Set(dataPipeline.dataModelFiles)],
      apiHandlerFiles: [...new Set(dataPipeline.apiHandlerFiles)],
    },
    docCoverage,
    dependencyDirection,
    groupImportsFrom,
    groupImportedBy,
    fileStats: {
      totalFileNodes: fileNodes.length,
      filesPerGroup,
      nodeTypeCounts,
    },
    fileFanIn,
    fileFanOut,
    topFanIn,
    topFanOut,
  };

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 1), 'utf8');
  console.log('OK total=' + fileNodes.length + ' groups=' + totalGroups);
}

try {
  main();
} catch (err) {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
}
