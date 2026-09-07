# `org` profile — Organization structure

**Status:** implemented · **Depends on:** `_core` · **Source standard:** [Popolo](https://www.popoloproject.com), W3C ORG

## What this profile is for

`_core` already defines Organization, Person, and Role, so this profile does not redefine
them. What `_core` cannot express is the **temporal and publishing layer**:

- A `Role` binds a person to a body for a span of time. When nobody holds an office, there is
  no Role — and the office still exists. `_core` has no way to say *this seat is empty*.
- A list of officeholders is not a succession. Nothing groups "the people who have been
  mayor" into a single office with a history.
- A pile of entity files is not a directory. Nothing states what the set contains, when it
  was last current, who stands behind it, or what conformance level it claims.

schema.org has no concept for any of this. It has no vacancy, no incumbency, and no
succession — `successorOf` exists but is for products. So this profile mints one class,
`gs:Post`, and the small number of properties that hang off it.

## Post

A **Post** is an office that exists independently of whoever holds it: *Mayor of Example
City*, *Councilmember, District 2*. It is the Popolo `Post`, and it is the hinge that makes
vacancy and succession expressible.

```
Post  ←── post ──  Role  ── member ──→  Person
 │                  │
 │                  └── startDate / endDate   (one tenure)
 └── vacantSince, termDuration, maximumTermCount, roleClassification
```

One Post, many Roles over time, at most one of them current. A vacancy is a Post whose
`vacantSince` is set and which no open Role points at.

`namedPosition` and `numberedPosition` are real schema.org Role properties and carry seat
identity, so no term was minted for them.

## Vacancy is data, not absence

`vacantSince` exists because omitting a vacancy is indistinguishable from never having
collected the information. A consumer cannot tell "this seat is empty" from "this publisher
does not list seats." Stating the vacancy explicitly is the difference between a directory
that can be audited and one that cannot.

## Directory

A `Directory` is a `schema:DataFeed` packaging the whole structure into one dated,
attributed, retrievable document. A consumer polls one URL and reads `dateModified` to learn
whether anything changed, rather than crawling every entity.

`conformsTo` carries the claimed conformance level (SPEC §4), which is how a small authority
signals that it is publishing Core rather than failing at Standard.

## Files

| Schema | Type | Purpose |
|---|---|---|
| `schema/post.schema.json` | `gs:Post` | An office, independent of its holder. |
| `schema/directory.schema.json` | `schema:DataFeed` | The packaged, dated org structure. |
| `codelists/role-classification.json` | `DefinedTermSet` | How an office is filled. |

`roleClassification` is mechanism-based (elected, appointed, employed, ex officio, volunteer,
hereditary) rather than title-based, because job titles do not translate across countries but
the mechanism of appointment does.
