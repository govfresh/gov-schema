# `permits` profile — Permits and licences

**Status:** implemented · **Depends on:** `_core`, `code`, `budget` · **Standard:** BLDS and national equivalents · **schema.org:** `GovernmentPermit`

## What schema.org supplies, and what it does not

`GovernmentPermit` is a real type with seven real properties — `issuedBy`, `issuedThrough`,
`permitAudience`, `validFor`, `validFrom`, `validUntil`, `validIn`. That is the **grant**.

What it has nothing for is the **application that produced it**: who applied, when, what was
decided, what it concerns, what it cost, and on what conditions. That is where nearly all the
public interest lies, so those fields are minted here.

## Why the type list is generic

The same permission is a building permit in the US, planning permission in the UK, a *permis
de construire* in France and a *Baugenehmigung* in Germany. A code list of national names
would not travel, so `permitType` is deliberately coarse and publishers carry the local name
in `name`.

BLDS (the Building & Land Development Specification) is the closest existing standard and is
US-only, which is why this profile takes the `_core` identifier approach rather than adopting
BLDS wholesale.

## Refusals belong in the data

`permitStatus` includes `refused`, `withdrawn`, `revoked` and `expired` — not only the happy
path. **A dataset containing only granted permits cannot answer what proportion of
applications succeed**, which is one of the main questions asked of this data. The fixtures
include a refused planning application with the reason recorded.

## Processing time is the headline number

`applicationDate` with `decisionDate` is what makes *how long does this take* answerable — the
question residents and developers actually ask. The validator enforces the sequence: a permit
cannot be decided before it was applied for, completed before it was decided, or expire before
it becomes valid, and one marked `issued` or `completed` without a `decisionDate` is an error
because no processing time can be derived from it.

## Conditions change what a grant means

A permit granted subject to conditions is not the same as one granted outright, and `condition`
is the only field that shows the difference.

## Applicant is optional on purpose

Business licences name a business, and that is public. **A residential building permit ties a
named private individual to their home address** — which is a disclosure decision the
authority must take deliberately, not one the schema should force.

So `applicant` is never required. The fixtures show both: a company named on a commercial
conversion, and a residential roof replacement published with the works, the value and the
dates but no applicant and no street address. That is a legitimate, conformant record.

This is the same reasoning as the reporter-privacy rule in `requests`, applied to a case where
the data is more often genuinely public.

## Joins

`relatedLegislation` points at the provision a permit is granted under — a zoning chapter, a
licensing act — so a permit resolves to the law authorising it. `premises.parcelIdentifier`
is scheme-qualified because parcel numbering is national: the scheme matters as much as the
code.
