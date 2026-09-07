import fs from 'node:fs/promises'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')
const DIR = path.join(ROOT, 'examples', 'example-city')

/** Entities from the fixture set, with their cross-references resolved for display. */
export default async function () {
  let names = []
  try {
    names = (await fs.readdir(DIR)).filter((n) => n.endsWith('.jsonld')).sort()
  } catch {
    return { files: [], entities: [], refCount: 0 }
  }

  const files = []
  const entities = []
  for (const n of names) {
    const doc = JSON.parse(await fs.readFile(path.join(DIR, n), 'utf8'))
    const nodes = doc['@graph'] || [doc]
    files.push({ name: n, count: nodes.length, raw: JSON.stringify(doc, null, 2) })
    for (const node of nodes) {
      entities.push({
        id: node['@id'],
        type: Array.isArray(node['@type']) ? node['@type'][0] : node['@type'],
        name: node.name,
        file: n,
        raw: JSON.stringify(node, null, 2),
      })
    }
  }

  // Count reference-shaped objects, matching tools/validate.py's definition.
  let refCount = 0
  const walk = (v) => {
    if (Array.isArray(v)) return v.forEach(walk)
    if (v && typeof v === 'object') {
      for (const [k, val] of Object.entries(v)) {
        if (k === '@id') continue
        if (val && typeof val === 'object' && !Array.isArray(val) && val['@id']) {
          const keys = Object.keys(val)
          if (keys.every((x) => ['@id', '@type', 'name'].includes(x))) refCount++
          else walk(val)
        } else walk(val)
      }
    }
  }
  entities.forEach((e) => walk(JSON.parse(e.raw)))

  return { files, entities, refCount }
}
