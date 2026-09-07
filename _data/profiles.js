import fs from 'node:fs/promises'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')

/** Profiles with schemas on disk are "implemented"; the rest are read as planned stubs. */
const IMPLEMENTED = [
  { dir: '_core', slug: 'core', name: 'Core', source: 'Popolo, W3C ORG' },
  { dir: 'org', slug: 'org', name: 'Organization structure', source: 'Popolo, W3C ORG' },
  { dir: 'code', slug: 'code', name: 'Legislation and codes', source: 'Akoma Ntoso, ELI' },
  { dir: 'meetings', slug: 'meetings', name: 'Meetings and votes', source: 'Popolo, Open Civic Data' },
  { dir: 'requests', slug: 'requests', name: 'Service requests', source: 'Open311 GeoReport v2' },
  { dir: 'budget', slug: 'budget', name: 'Budgets and spending', source: 'Fiscal Data Package, COFOG, GFSM 2014' },
  { dir: 'procurement', slug: 'procurement', name: 'Procurement and contracts', source: 'Open Contracting Data Standard' },
  { dir: 'catalog', slug: 'catalog', name: 'Discovery and data catalogue', source: 'DCAT / DCAT-AP' },
  { dir: 'alerts', slug: 'alerts', name: 'Public warnings and notices', source: 'Common Alerting Protocol (OASIS)' },
  { dir: 'permits', slug: 'permits', name: 'Permits and licences', source: 'BLDS, national equivalents' },
  { dir: 'elections', slug: 'elections', name: 'Elections and results', source: 'NIST SP 1500-100, VIP' },
]
const PLANNED = []

async function readJson(p) {
  return JSON.parse(await fs.readFile(p, 'utf8'))
}

async function readDirJson(dir) {
  let names
  try {
    names = await fs.readdir(dir)
  } catch {
    return []
  }
  const out = []
  for (const n of names.filter((n) => n.endsWith('.json')).sort()) {
    out.push({ file: n, ...(await readJson(path.join(dir, n))) })
  }
  return out
}

function toSchema(s) {
  const required = new Set(s.required || [])
  const fields = Object.entries(s.properties || {})
    .filter(([name]) => name !== '@context')
    .map(([name, def]) => ({
      name,
      required: required.has(name),
      def,
      description: def.description || '',
    }))
  return {
    file: s.file,
    slug: s.file.replace('.schema.json', ''),
    title: s.title,
    description: s.description,
    id: s.$id,
    fields,
    requiredCount: required.size,
    fieldCount: fields.length,
  }
}

function toCodelist(c) {
  return {
    file: c.file,
    slug: c.file.replace('.json', ''),
    name: c.name,
    description: c.description,
    id: c['@id'],
    termSegment: (c['@id'] || '').split('/').pop(),
    rawTermIds: Object.fromEntries(
      (c.hasDefinedTerm || [])
        .filter((t) => (t['@id'] || '').startsWith('gs:'))
        .map((t) => [t.termCode, t['@id'].slice(3)]),
    ),
    terms: (c.hasDefinedTerm || []).map((t) => ({
      code: t.termCode,
      name: t.name,
      description: t.description,
    })),
  }
}

/**
 * Documentation is generated from the schemas themselves, so a field can never be
 * documented here and absent there. Adding a property to a schema is the only way
 * to add it to these pages.
 */
export default async function () {
  const built = []
  for (const p of IMPLEMENTED) {
    const base = path.join(ROOT, 'profiles', p.dir)
    built.push({
      ...p,
      urlBase: p.dir === '_core' ? '/v1/_core/' : `/v1/${p.dir}/`,
      schemas: (await readDirJson(path.join(base, 'schema'))).map(toSchema),
      codelists: (await readDirJson(path.join(base, 'codelists'))).map(toCodelist),
    })
  }

  const planned = []
  for (const d of PLANNED) {
    try {
      const txt = await fs.readFile(path.join(ROOT, 'profiles', d, 'README.md'), 'utf8')
      planned.push({
        slug: d,
        title: txt.match(/^# `[^`]+` profile — (.+)$/m)?.[1] || d,
        source: txt.match(/\*\*Source standard:\*\* (.+)$/m)?.[1] || '',
        depends: txt.match(/\*\*Depends on:\*\* (.+)$/m)?.[1] || '',
      })
    } catch {}
  }

  // Every individual term, so each code-list value gets a dereferenceable page.
  // Published documents expand values into these IRIs, so a 404 here means a document
  // points at nothing.
  const terms = []
  for (const b of built) {
    for (const c of b.codelists) {
      for (const t of c.terms) {
        const raw = (c.rawTermIds || {})[t.code]
        if (!raw) continue
        terms.push({
          path: raw,                       // e.g. "level/municipal"
          code: t.code,
          name: t.name,
          description: t.description,
          setName: c.name,
          setSegment: c.termSegment,
          setUrl: c.id,
          profile: b.slug,
          file: c.file,
        })
      }
    }
  }

  // Flat views, so existing templates keep working.
  const schemas = built.flatMap((b) => b.schemas.map((s) => ({ ...s, profile: b.slug })))
  const codelists = built.flatMap((b) => b.codelists.map((c) => ({ ...c, profile: b.slug })))

  return { built, planned, schemas, codelists, terms }
}
