import fs from 'node:fs/promises'
import path from 'node:path'
import MarkdownIt from 'markdown-it'

const ROOT = path.resolve(import.meta.dirname, '..')
const md = new MarkdownIt({ html: true, linkify: true })

/**
 * SPEC.md is rendered here rather than duplicated into a template, so the
 * published specification and the repository file can never disagree.
 */
export default async function () {
  const read = async (f) => {
    try {
      return await fs.readFile(path.join(ROOT, f), 'utf8')
    } catch {
      return ''
    }
  }
  const spec = await read('SPEC.md')
  // Drop the leading H1; the page template supplies its own.
  const body = spec.replace(/^#\s+.+\n/, '')
  return {
    spec: md.render(body),
    specHeadings: [...body.matchAll(/^##\s+(.+)$/gm)].map((m) => ({
      text: m[1],
      slug: m[1].toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
    })),
  }
}
