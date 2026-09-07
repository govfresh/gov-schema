import { IdAttributePlugin } from '@11ty/eleventy'
import pluginSyntaxHighlight from '@11ty/eleventy-plugin-syntaxhighlight'
import pluginNavigation from '@11ty/eleventy-navigation'

/** @param {import("@11ty/eleventy").UserConfig} eleventyConfig */
export default async function (eleventyConfig) {
  eleventyConfig.addPlugin(pluginSyntaxHighlight, { preAttributes: { tabindex: 0 } })
  eleventyConfig.addPlugin(pluginNavigation)
  eleventyConfig.addPlugin(IdAttributePlugin)

  // --- static assets -------------------------------------------------------
  eleventyConfig.addPassthroughCopy({ './public/': '/' })

  // --- the namespace itself ------------------------------------------------
  // These are not documentation. Every published gov-schema document pins these
  // exact URLs in its @context and $id, and SPEC section 6 makes them immutable.
  // If a path here changes, previously published data stops resolving.
  eleventyConfig.addPassthroughCopy({ './context/v1/': '/v1/' })
  eleventyConfig.addPassthroughCopy({ './profiles/_core/schema/': '/v1/_core/' })
  eleventyConfig.addPassthroughCopy({ './vocabulary/govschema.ttl': '/v1/govschema.ttl' })
  eleventyConfig.addPassthroughCopy({ './profiles/org/schema/': '/v1/org/' })
  eleventyConfig.addPassthroughCopy({ './profiles/_core/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/org/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/code/schema/': '/v1/code/' })
  eleventyConfig.addPassthroughCopy({ './profiles/code/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/meetings/schema/': '/v1/meetings/' })
  eleventyConfig.addPassthroughCopy({ './profiles/meetings/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/requests/schema/': '/v1/requests/' })
  eleventyConfig.addPassthroughCopy({ './profiles/requests/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/budget/schema/': '/v1/budget/' })
  eleventyConfig.addPassthroughCopy({ './profiles/budget/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/procurement/schema/': '/v1/procurement/' })
  eleventyConfig.addPassthroughCopy({ './profiles/procurement/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/catalog/schema/': '/v1/catalog/' })
  eleventyConfig.addPassthroughCopy({ './profiles/catalog/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/alerts/schema/': '/v1/alerts/' })
  eleventyConfig.addPassthroughCopy({ './profiles/alerts/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/permits/schema/': '/v1/permits/' })
  eleventyConfig.addPassthroughCopy({ './profiles/permits/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/elections/schema/': '/v1/elections/' })
  eleventyConfig.addPassthroughCopy({ './profiles/elections/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './profiles/services/schema/': '/v1/services/' })
  eleventyConfig.addPassthroughCopy({ './profiles/services/codelists/': '/v1/codelists/' })
  eleventyConfig.addPassthroughCopy({ './examples/': '/examples/' })

  eleventyConfig.addWatchTarget('./profiles/')
  eleventyConfig.addWatchTarget('./context/')
  eleventyConfig.addWatchTarget('./SPEC.md')

  // --- filters -------------------------------------------------------------
  eleventyConfig.addFilter('jsonPretty', (v) => JSON.stringify(v, null, 2))

  // Render a JSON Schema "type" cell: enum, $ref, or plain type.
  eleventyConfig.addFilter('fieldType', (field) => {
    if (!field) return ''
    if (field.$ref) return field.$ref.replace('.schema.json', '')
    if (field.const) return `"${field.const}"`
    if (field.enum) return field.enum.map((e) => `"${e}"`).join(' | ')
    if (field.type === 'array' && field.items) {
      const inner = field.items.$ref
        ? field.items.$ref.replace('.schema.json', '')
        : field.items.type || 'object'
      return `${inner}[]`
    }
    return field.type || 'object'
  })

  // Pull the schema.org term a description mentions, for the mapping column.
  eleventyConfig.addFilter('schemaOrgTerm', (desc) => {
    if (!desc) return null
    const m = desc.match(/schema:([A-Za-z]+)/)
    return m ? m[1] : null
  })

  eleventyConfig.addFilter('count', (o) => (o ? Object.keys(o).length : 0))
}

export const config = {
  templateFormats: ['md', 'njk', 'html'],
  markdownTemplateEngine: 'njk',
  htmlTemplateEngine: 'njk',
  dir: {
    input: 'content',
    includes: '../_includes',
    data: '../_data',
    output: '_site',
  },
}
