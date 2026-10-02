#!/usr/bin/env node
/* Understand-Anything graph validator. argv[2]=graph json, argv[3]=output json, argv[4]=scan-result json (optional) */
'use strict';
const fs = require('fs');
const path = require('path');

const graphPath = process.argv[2];
const outPath = process.argv[3];
const scanPath = process.argv[4];

if (!graphPath || !outPath) {
  console.error('usage: node ua-graph-validate.js <graph.json> <out.json> [scan-result.json]');
  process.exit(1);
}

let graph;
try {
  graph = JSON.parse(fs.readFileSync(graphPath, 'utf8'));
} catch (e) {
  console.error('Failed to read/parse graph: ' + e.message);
  process.exit(1);
}

let scan = null;
if (scanPath && fs.existsSync(scanPath)) {
  try { scan = JSON.parse(fs.readFileSync(scanPath, 'utf8')); }
  catch (e) { console.error('WARN: could not parse scan-result: ' + e.message); }
}

const issues = [];
const warnings = [];

const NODE_TYPES = new Set(['file','function','class','module','concept','config','document','service','table','endpoint','pipeline','schema','resource','domain','flow','step']);
const ID_PREFIXES = ['file:','function:','class:','module:','concept:','config:','document:','service:','table:','endpoint:','pipeline:','schema:','resource:','domain:','flow:','step:'];
const EDGE_TYPES = new Set(['imports','exports','contains','inherits','implements','calls','subscribes','publishes','middleware','reads_from','writes_to','transforms','validates','depends_on','tested_by','configures','related','similar_to','deploys','serves','migrates','documents','provisions','routes','defines_schema','triggers','contains_flow','flow_step','cross_domain']);
const DIRECTIONS = new Set(['forward','backward','bidirectional']);
const COMPLEXITY = new Set(['simple','moderate','complex']);
const FILE_LEVEL_TYPES = new Set(['file','config','document','service','pipeline','table','schema','resource','endpoint']);

const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
const edges = Array.isArray(graph.edges) ? graph.edges : [];
const layers = Array.isArray(graph.layers) ? graph.layers : [];
let tourSteps = [];
if (Array.isArray(graph.tour)) tourSteps = graph.tour;
else if (graph.tour && Array.isArray(graph.tour.steps)) tourSteps = graph.tour.steps;
else if (Array.isArray(graph.tourSteps)) tourSteps = graph.tourSteps;

const isDomainGraph = nodes.some(n => n && (n.type === 'domain' || n.type === 'flow' || n.type === 'step'));

/* ---------- Check 5: uniqueness (first, so id map is sane) ---------- */
const idIndices = new Map();
nodes.forEach((n, i) => {
  const id = n && typeof n.id === 'string' ? n.id : null;
  if (id === null) return;
  if (!idIndices.has(id)) idIndices.set(id, []);
  idIndices.get(id).push(i);
});
for (const [id, idxs] of idIndices) {
  if (idxs.length > 1) issues.push(`Duplicate node ID '${id}' appears ${idxs.length} times at node indices [${idxs.join(', ')}]`);
}
const nodeById = new Map();
nodes.forEach(n => { if (n && typeof n.id === 'string' && !nodeById.has(n.id)) nodeById.set(n.id, n); });
const nodeIds = new Set(nodeById.keys());

/* ---------- Check 1: node schema ---------- */
const mojibakePattern = /[ÂÃâ][-¿]|�|â€|Ã‚|Â /;
const nonAsciiChars = new Map();

function scanText(label, text) {
  if (typeof text !== 'string') return;
  if (mojibakePattern.test(text)) warnings.push(`Possible mojibake in ${label}: "${text.slice(0, 120)}"`);
  for (const ch of text) {
    const cp = ch.codePointAt(0);
    if (cp > 127) {
      const key = 'U+' + cp.toString(16).toUpperCase().padStart(4, '0');
      nonAsciiChars.set(key, (nonAsciiChars.get(key) || 0) + 1);
    }
  }
}

const nodeTypes = {};
nodes.forEach((n, i) => {
  const loc = `node index ${i}` + (n && n.id ? ` ('${n.id}')` : '');
  if (!n || typeof n !== 'object') { issues.push(`${loc} is not an object`); return; }

  if (typeof n.id !== 'string' || n.id.trim() === '') {
    issues.push(`${loc} has missing or empty 'id'`);
  } else if (!ID_PREFIXES.some(p => n.id.startsWith(p))) {
    issues.push(`${loc} has id '${n.id}' which does not start with a valid prefix`);
  }

  if (typeof n.type !== 'string' || n.type.trim() === '') issues.push(`${loc} has missing or empty 'type'`);
  else if (!NODE_TYPES.has(n.type)) issues.push(`${loc} has invalid type '${n.type}'`);
  else nodeTypes[n.type] = (nodeTypes[n.type] || 0) + 1;

  if (typeof n.name !== 'string' || n.name.trim() === '') issues.push(`${loc} has missing or empty 'name'`);
  if (typeof n.summary !== 'string' || n.summary.trim() === '') issues.push(`${loc} has missing or empty 'summary'`);

  if (!Array.isArray(n.tags)) issues.push(`${loc} has missing or non-array 'tags'`);
  else if (n.tags.length < 1) issues.push(`${loc} has an empty 'tags' array`);
  else {
    const bad = n.tags.filter(t => typeof t !== 'string' || t.trim() === '' || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(t));
    if (bad.length) warnings.push(`${loc} has non-lowercase/non-hyphenated tags: ${JSON.stringify(bad.slice(0, 5))}`);
  }

  if (typeof n.complexity !== 'string' || !COMPLEXITY.has(n.complexity)) {
    issues.push(`${loc} has missing or invalid 'complexity': ${JSON.stringify(n.complexity)}`);
  }

  // Check 9: type / id prefix consistency
  if (typeof n.type === 'string' && typeof n.id === 'string' && NODE_TYPES.has(n.type)) {
    if (!n.id.startsWith(n.type + ':')) {
      warnings.push(`Node '${n.id}' has type '${n.type}' but its ID prefix does not match (expected '${n.type}:')`);
    }
  }

  // Check 7: summary quality
  if (typeof n.summary === 'string' && typeof n.name === 'string') {
    const s = n.summary.trim();
    const base = n.name.trim();
    const fileBase = typeof n.filePath === 'string' ? path.basename(n.filePath) : null;
    if (s && (s === base || (fileBase && s === fileBase) || s.toLowerCase() === base.toLowerCase())) {
      warnings.push(`Node '${n.id}' has a generic summary that merely restates its name ("${s.slice(0, 80)}")`);
    } else if (s.length > 0 && s.length < 25) {
      warnings.push(`Node '${n.id}' has a very short summary (${s.length} chars): "${s}"`);
    }
  }

  scanText(`node '${n.id}' name`, n.name);
  scanText(`node '${n.id}' summary`, n.summary);
  if (Array.isArray(n.tags)) n.tags.forEach(t => scanText(`node '${n.id}' tag`, t));
});

/* ---------- Check 1 + 2: edge schema and referential integrity ---------- */
const edgeTypes = {};
const degree = new Map();
nodes.forEach(n => { if (n && n.id) degree.set(n.id, 0); });
const edgeKeySeen = new Map();

edges.forEach((e, i) => {
  const loc = `Edge at index ${i}`;
  if (!e || typeof e !== 'object') { issues.push(`${loc} is not an object`); return; }

  const src = e.source, tgt = e.target;
  if (typeof src !== 'string' || src.trim() === '') issues.push(`${loc} has missing or empty 'source'`);
  else if (!nodeIds.has(src)) issues.push(`${loc} references non-existent source node '${src}' (type '${e.type}', target '${tgt}')`);

  if (typeof tgt !== 'string' || tgt.trim() === '') issues.push(`${loc} has missing or empty 'target'`);
  else if (!nodeIds.has(tgt)) issues.push(`${loc} references non-existent target node '${tgt}' (type '${e.type}', source '${src}')`);

  if (typeof e.type !== 'string' || e.type.trim() === '') issues.push(`${loc} has missing or empty 'type'`);
  else if (!EDGE_TYPES.has(e.type)) issues.push(`${loc} has invalid edge type '${e.type}' (source '${src}', target '${tgt}')`);
  else edgeTypes[e.type] = (edgeTypes[e.type] || 0) + 1;

  if (typeof e.direction !== 'string' || !DIRECTIONS.has(e.direction)) {
    issues.push(`${loc} has missing or invalid 'direction': ${JSON.stringify(e.direction)}`);
  }

  if (typeof e.weight !== 'number' || Number.isNaN(e.weight)) {
    issues.push(`${loc} has missing or non-numeric 'weight': ${JSON.stringify(e.weight)}`);
  } else if (e.weight < 0 || e.weight > 1) {
    issues.push(`${loc} has weight ${e.weight} outside the 0.0-1.0 range (source '${src}', target '${tgt}', type '${e.type}')`);
  }

  if (typeof src === 'string' && typeof tgt === 'string' && src === tgt) {
    warnings.push(`${loc} is self-referencing: '${src}' --${e.type}--> itself`);
  }

  if (typeof src === 'string' && typeof tgt === 'string' && typeof e.type === 'string') {
    const k = `${src}|${e.type}|${tgt}`;
    if (edgeKeySeen.has(k)) warnings.push(`Duplicate edge '${src}' --${e.type}--> '${tgt}' at indices ${edgeKeySeen.get(k)} and ${i}`);
    else edgeKeySeen.set(k, i);
  }

  if (typeof src === 'string' && degree.has(src)) degree.set(src, degree.get(src) + 1);
  if (typeof tgt === 'string' && degree.has(tgt)) degree.set(tgt, degree.get(tgt) + 1);

  scanText(`edge ${i} description`, e.description || e.label);
});

/* ---------- Check 3: completeness ---------- */
if (nodes.length < 1) issues.push('Graph has zero nodes');
if (edges.length < 1) issues.push('Graph has zero edges');
if (layers.length < 1) {
  if (isDomainGraph) warnings.push('Domain graph has zero layers (relaxed to a warning)');
  else issues.push('Graph has zero layers');
}
if (tourSteps.length < 1) {
  if (isDomainGraph) warnings.push('Domain graph has zero tour steps (relaxed to a warning)');
  else issues.push('Graph has zero tour steps');
}

/* ---------- Check 2 + 4: layer references and coverage ---------- */
const nodeLayerCount = new Map();
layers.forEach((l, li) => {
  const lname = (l && (l.name || l.id)) || `index ${li}`;
  const ids = l && Array.isArray(l.nodeIds) ? l.nodeIds : null;
  if (!ids) { issues.push(`Layer '${lname}' (index ${li}) has a missing or non-array 'nodeIds'`); return; }
  if (ids.length === 0) issues.push(`Layer '${lname}' (index ${li}) has an empty 'nodeIds' array`);
  const seenHere = new Set();
  ids.forEach(id => {
    if (!nodeIds.has(id)) issues.push(`Layer '${lname}' (index ${li}) nodeIds references non-existent node '${id}'`);
    if (seenHere.has(id)) warnings.push(`Layer '${lname}' (index ${li}) lists node '${id}' more than once`);
    seenHere.add(id);
    nodeLayerCount.set(id, (nodeLayerCount.get(id) || 0) + 1);
  });
});

const fileLevelNodes = nodes.filter(n => n && typeof n.id === 'string' && FILE_LEVEL_TYPES.has(n.type));
const skipLayerCoverage = isDomainGraph && layers.length === 0;
if (!skipLayerCoverage) {
  const missing = [], multi = [];
  fileLevelNodes.forEach(n => {
    const c = nodeLayerCount.get(n.id) || 0;
    if (c === 0) missing.push(n.id);
    else if (c > 1) multi.push(`${n.id} (in ${c} layers)`);
  });
  if (missing.length) {
    issues.push(`${missing.length} file-level node(s) appear in no layer: ${missing.slice(0, 20).join(', ')}${missing.length > 20 ? ' ...' : ''}`);
  }
  if (multi.length) {
    issues.push(`${multi.length} file-level node(s) appear in more than one layer: ${multi.slice(0, 20).join(', ')}${multi.length > 20 ? ' ...' : ''}`);
  }
}
// non-file-level nodes placed in layers (informational)
const nonFileInLayers = [];
for (const id of nodeLayerCount.keys()) {
  const n = nodeById.get(id);
  if (n && !FILE_LEVEL_TYPES.has(n.type)) nonFileInLayers.push(id);
}
if (nonFileInLayers.length) {
  warnings.push(`${nonFileInLayers.length} non-file-level node(s) are assigned to layers: ${nonFileInLayers.slice(0, 10).join(', ')}${nonFileInLayers.length > 10 ? ' ...' : ''}`);
}

/* ---------- Check 2 + 6: tour ---------- */
const tourNodeIdsAll = [];
tourSteps.forEach((s, si) => {
  const sloc = `Tour step index ${si}` + (s && s.title ? ` ('${s.title}')` : '');
  if (!s || typeof s !== 'object') { issues.push(`${sloc} is not an object`); return; }
  const ids = Array.isArray(s.nodeIds) ? s.nodeIds : null;
  if (!ids) { issues.push(`${sloc} has a missing or non-array 'nodeIds'`); return; }
  if (ids.length < 1) warnings.push(`${sloc} has an empty 'nodeIds' array`);
  ids.forEach(id => {
    tourNodeIdsAll.push(id);
    if (!nodeIds.has(id)) issues.push(`${sloc} nodeIds references non-existent node '${id}'`);
  });
});
const orders = tourSteps.map(s => (s && typeof s.order === 'number') ? s.order : null);
if (orders.some(o => o === null)) {
  warnings.push(`${orders.filter(o => o === null).length} tour step(s) have a missing or non-numeric 'order'`);
}
const presentOrders = orders.filter(o => o !== null);
const dupOrders = presentOrders.filter((o, i) => presentOrders.indexOf(o) !== i);
if (dupOrders.length) warnings.push(`Tour has duplicate 'order' values: ${[...new Set(dupOrders)].join(', ')}`);
const sorted = [...presentOrders].sort((a, b) => a - b);
const expected = presentOrders.map((_, i) => i + 1);
if (JSON.stringify(sorted) !== JSON.stringify(expected)) {
  warnings.push(`Tour 'order' values are not sequential from 1 (got [${sorted.join(', ')}])`);
}
if (tourSteps.length > 0 && (tourSteps.length < 5 || tourSteps.length > 15)) {
  warnings.push(`Tour has ${tourSteps.length} steps, outside the recommended 5-15 range`);
}
// tour nodes that are not file-level
const tourNonFileLevel = [...new Set(tourNodeIdsAll)].filter(id => {
  const n = nodeById.get(id);
  return n && !FILE_LEVEL_TYPES.has(n.type);
});
if (tourNonFileLevel.length) {
  warnings.push(`${tourNonFileLevel.length} tour node reference(s) are not file-level types: ${tourNonFileLevel.slice(0, 10).join(', ')}`);
}

/* ---------- Check 7: orphans ---------- */
const orphans = [];
for (const [id, d] of degree) if (d === 0) orphans.push(id);
if (orphans.length) {
  const byType = {};
  orphans.forEach(id => { const t = (nodeById.get(id) || {}).type || '?'; byType[t] = (byType[t] || 0) + 1; });
  warnings.push(`${orphans.length} orphan node(s) with zero edges (by type: ${JSON.stringify(byType)}): ${orphans.slice(0, 15).join(', ')}${orphans.length > 15 ? ' ...' : ''}`);
}

/* ---------- Check 8: non-code node expected edges ---------- */
const outByType = new Map(), inByType = new Map();
function pushMap(m, id, t) { if (!m.has(id)) m.set(id, new Set()); m.get(id).add(t); }
edges.forEach(e => {
  if (!e || typeof e.type !== 'string') return;
  if (typeof e.source === 'string') pushMap(outByType, e.source, e.type);
  if (typeof e.target === 'string') pushMap(inByType, e.target, e.type);
});
function hasAnyEdge(id, types) {
  const o = outByType.get(id) || new Set();
  const inn = inByType.get(id) || new Set();
  return types.some(t => o.has(t) || inn.has(t));
}
const EXPECTED = {
  document: ['documents'],
  service: ['deploys', 'depends_on'],
  pipeline: ['triggers'],
  table: ['migrates', 'defines_schema'],
  schema: ['defines_schema'],
  domain: ['contains_flow'],
  flow: ['flow_step'],
};
const missingExpected = {};
nodes.forEach(n => {
  if (!n || typeof n.id !== 'string') return;
  const exp = EXPECTED[n.type];
  if (!exp) return;
  if (!hasAnyEdge(n.id, exp)) {
    if (!missingExpected[n.type]) missingExpected[n.type] = [];
    missingExpected[n.type].push(n.id);
  }
});
Object.keys(missingExpected).forEach(t => {
  const list = missingExpected[t];
  warnings.push(`${list.length} ${t} node(s) have no '${EXPECTED[t].join("'/'")}' edge: ${list.slice(0, 12).join(', ')}${list.length > 12 ? ' ...' : ''}`);
});

/* ---------- Extra: cross-validation against the scan inventory ---------- */
const extra = {};
function norm(p) { return typeof p === 'string' ? p.replace(/\\/g, '/').replace(/^\.\//, '') : p; }

if (scan) {
  const scanFiles = Array.isArray(scan.files) ? scan.files : [];
  const scanPaths = new Set(scanFiles.map(f => norm(f && f.path)).filter(Boolean));
  extra.scanFileCount = scanPaths.size;

  const fileLevelByPath = new Map();
  fileLevelNodes.forEach(n => {
    const p = norm(n.filePath);
    if (!p) return;
    if (!fileLevelByPath.has(p)) fileLevelByPath.set(p, []);
    fileLevelByPath.get(p).push(n);
  });

  // files in scan with no file-level node
  const missingFiles = [...scanPaths].filter(p => !fileLevelByPath.has(p));
  extra.scannedFilesWithoutNode = missingFiles.length;
  if (missingFiles.length) {
    issues.push(`${missingFiles.length} scanned file(s) have no corresponding file-level node: ${missingFiles.slice(0, 20).join(', ')}${missingFiles.length > 20 ? ' ...' : ''}`);
  }

  // file-level nodes whose filePath is not in the scan inventory
  const unknownPaths = [];
  fileLevelNodes.forEach(n => {
    const p = norm(n.filePath);
    if (!p) { unknownPaths.push(`${n.id} (no filePath)`); return; }
    if (!scanPaths.has(p)) unknownPaths.push(`${n.id} -> ${p}`);
  });
  extra.fileLevelNodesWithUnknownPath = unknownPaths.length;
  if (unknownPaths.length) {
    warnings.push(`${unknownPaths.length} file-level node(s) have a filePath absent from the scan inventory: ${unknownPaths.slice(0, 12).join('; ')}${unknownPaths.length > 12 ? ' ...' : ''}`);
  }

  // identity nodes = exactly one file-level node per scanned path, counted by type
  const identityNodes = [];
  const childNodes = [];
  fileLevelNodes.forEach(n => {
    const p = norm(n.filePath);
    if (p && scanPaths.has(p)) {
      const siblings = fileLevelByPath.get(p) || [];
      // identity node = the one whose name matches the basename, else the first
      identityNodes.push(n);
    }
  });
  // determine identity vs child: one identity per scanned path
  const identityByPath = new Map();
  for (const [p, list] of fileLevelByPath) {
    if (!scanPaths.has(p)) continue;
    const base = path.basename(p);
    let pick = list.find(n => n.name === base) || list.find(n => norm(n.id).endsWith(p)) || list[0];
    identityByPath.set(p, pick);
  }
  const identitySet = new Set([...identityByPath.values()].map(n => n.id));
  fileLevelNodes.forEach(n => { if (!identitySet.has(n.id)) childNodes.push(n); });

  extra.fileIdentityNodes = identitySet.size;
  extra.fileLevelChildNodes = childNodes.length;
  const idTypes = {};
  identityByPath.forEach(n => { idTypes[n.type] = (idTypes[n.type] || 0) + 1; });
  extra.fileIdentityNodeTypes = idTypes;
  const childTypes = {};
  childNodes.forEach(n => { childTypes[n.type] = (childTypes[n.type] || 0) + 1; });
  extra.fileLevelChildNodeTypes = childTypes;

  // every child node should have an inbound 'contains' edge from a parent
  const containsInbound = new Map();
  edges.forEach(e => {
    if (e && e.type === 'contains' && typeof e.target === 'string') {
      if (!containsInbound.has(e.target)) containsInbound.set(e.target, []);
      containsInbound.get(e.target).push(e.source);
    }
  });
  const childNoContains = childNodes.filter(n => !containsInbound.has(n.id));
  extra.childNodesWithoutContainsParent = childNoContains.length;
  if (childNoContains.length) {
    warnings.push(`${childNoContains.length} file-level child node(s) have no inbound 'contains' edge from a parent: ${childNoContains.slice(0, 12).map(n => n.id).join(', ')}`);
  }
  // and the contains parent should be the node for their declared filePath
  const childWrongParent = [];
  childNodes.forEach(n => {
    const parents = containsInbound.get(n.id);
    if (!parents) return;
    const p = norm(n.filePath);
    const ident = p ? identityByPath.get(p) : null;
    if (ident && !parents.includes(ident.id)) childWrongParent.push(`${n.id} (parents: ${parents.join('/')}, expected ${ident.id})`);
  });
  extra.childNodesWithUnexpectedParent = childWrongParent.length;
  if (childWrongParent.length) {
    warnings.push(`${childWrongParent.length} file-level child node(s) are contained by something other than their declared filePath's node: ${childWrongParent.slice(0, 8).join('; ')}`);
  }

  // imports edges vs importMap
  const importMap = scan.importMap;
  let mapPairs = new Set();
  let mapCount = 0;
  if (importMap && typeof importMap === 'object') {
    if (Array.isArray(importMap)) {
      importMap.forEach(entry => {
        if (!entry) return;
        const from = norm(entry.from || entry.source || entry.file);
        const tos = entry.to || entry.target || entry.imports || entry.resolved;
        const list = Array.isArray(tos) ? tos : (tos ? [tos] : []);
        list.forEach(t => { mapPairs.add(from + '=>' + norm(t)); mapCount++; });
      });
    } else {
      Object.keys(importMap).forEach(from => {
        const v = importMap[from];
        const list = Array.isArray(v) ? v : (v && Array.isArray(v.imports) ? v.imports : []);
        list.forEach(t => {
          const tt = typeof t === 'string' ? t : (t && (t.resolved || t.path || t.target));
          if (tt) { mapPairs.add(norm(from) + '=>' + norm(tt)); mapCount++; }
        });
      });
    }
  }
  extra.importMapEntries = mapCount;
  extra.importMapUniquePairs = mapPairs.size;

  const importEdges = edges.filter(e => e && e.type === 'imports');
  extra.importEdges = importEdges.length;

  function pathOf(id) {
    const n = nodeById.get(id);
    return n ? norm(n.filePath) : null;
  }
  const edgePairs = new Set();
  const unbacked = [];
  importEdges.forEach((e, i) => {
    const sp = pathOf(e.source), tp = pathOf(e.target);
    if (!sp || !tp) { unbacked.push(`${e.source} -> ${e.target} (node filePath missing)`); return; }
    const k = sp + '=>' + tp;
    edgePairs.add(k);
    if (mapPairs.size && !mapPairs.has(k)) unbacked.push(`${sp} -> ${tp}`);
  });
  extra.importEdgesWithoutMapBacking = unbacked.length;
  if (mapPairs.size && unbacked.length) {
    warnings.push(`${unbacked.length} 'imports' edge(s) have no matching entry in the scan importMap: ${unbacked.slice(0, 10).join('; ')}${unbacked.length > 10 ? ' ...' : ''}`);
  }
  const unmodelled = [...mapPairs].filter(k => !edgePairs.has(k));
  extra.importMapPairsWithoutEdge = unmodelled.length;
  if (mapPairs.size && unmodelled.length) {
    warnings.push(`${unmodelled.length} importMap pair(s) have no corresponding 'imports' edge: ${unmodelled.slice(0, 10).join('; ')}${unmodelled.length > 10 ? ' ...' : ''}`);
  }
}

/* ---------- Extra: non-ascii / mojibake summary ---------- */
extra.nonAsciiCodepoints = Object.fromEntries([...nonAsciiChars.entries()].sort((a, b) => b[1] - a[1]));

/* ---------- Extra: edge counts for the "dubious" region ---------- */
const DUBIOUS_TARGET_HINTS = ['manifest_reader', 'dag_scheduler'];
extra.dubiousRegionEdges = edges
  .filter(e => e && (e.type === 'configures' || e.type === 'documents' || e.type === 'defines_schema'))
  .filter(e => DUBIOUS_TARGET_HINTS.some(h => (String(e.target) + String(e.source)).includes(h)))
  .map(e => `${e.source} --${e.type}--> ${e.target} (weight ${e.weight})`);

extra.fileLevelNodeCount = fileLevelNodes.length;
extra.layerAssignedFileLevelNodes = fileLevelNodes.filter(n => (nodeLayerCount.get(n.id) || 0) === 1).length;
extra.tourNodeRefs = tourNodeIdsAll.length;
extra.tourUniqueNodeRefs = new Set(tourNodeIdsAll).size;
extra.isDomainGraph = isDomainGraph;
extra.orphanCount = orphans.length;
extra.orphansByType = (() => { const m = {}; orphans.forEach(id => { const t = (nodeById.get(id) || {}).type || '?'; m[t] = (m[t] || 0) + 1; }); return m; })();
extra.layerSizes = layers.map(l => ({ name: (l && (l.name || l.id)) || null, count: l && Array.isArray(l.nodeIds) ? l.nodeIds.length : null }));
extra.tourStepSizes = tourSteps.map(s => ({ order: s && s.order, title: s && s.title, count: s && Array.isArray(s.nodeIds) ? s.nodeIds.length : null }));

const result = {
  scriptCompleted: true,
  issues,
  warnings,
  stats: {
    totalNodes: nodes.length,
    totalEdges: edges.length,
    totalLayers: layers.length,
    tourSteps: tourSteps.length,
    nodeTypes,
    edgeTypes,
  },
  extra,
};

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(result, null, 2), 'utf8');
console.log(`OK nodes=${nodes.length} edges=${edges.length} layers=${layers.length} tour=${tourSteps.length} issues=${issues.length} warnings=${warnings.length}`);
process.exit(0);
