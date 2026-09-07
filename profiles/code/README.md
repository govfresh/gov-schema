# `code` profile — Legislation and municipal codes

**Status:** implemented · **Depends on:** `_core`, `meetings` · **Source standard:** [Akoma Ntoso](http://www.akomantoso.org) (OASIS LegalDocML), [ELI](https://eur-lex.europa.eu/eli-register/about.html)

## schema.org already does most of this

schema.org's legislation vocabulary derives from the European Legislation Identifier and
carries 21 `legislation*` properties. Almost everything a code needs already exists:

| Need | Property |
|---|---|
| Is it in force? | `legislationLegalForce` → `InForce` / `NotInForce` / `PartiallyInForce` |
| What did it change? | `legislationAmends`, `legislationRepeals`, `legislationChanges`, `legislationConsolidates`, `legislationCorrects`, `legislationCommences` |
| Which version is this? | `legislationDateVersion` — the point in time this description is valid for |
| Three distinct dates | `legislationDate` (adoption), `legislationDateOfApplicability`, `datePublished` |
| Who passed it? | `legislationPassedBy`, `legislationResponsible`, `legislationCountersignedBy` |

**Do not invent a status field.** A `legislationStatus: "Active"` string is the single most
common error in hand-rolled government schema, and `legislationLegalForce` already exists
with a real enumeration.

This profile therefore mints exactly one property, `gs:codificationLevel`, plus
`gs:enactedAt` to reach the meetings profile.

## The one real gap

`hasPart` nests parts but never says **what kind** of part. A code, a title, a chapter and a
section are all `Legislation` with `hasPart` between them, and nothing distinguishes a
chapter from a schedule. `codificationLevel` supplies that, as an extensible code list —
systems differ in which tiers they use and in what order, so nesting comes from `isPartOf`
rather than from an assumed fixed depth.

## Work and expression

`Legislation` is the law. `LegislationObject` is one *file* of it — and schema.org types it
as both `Legislation` and `MediaObject`, which is precisely the FRBR work/expression split
that ELI and Akoma Ntoso rely on.

The same law commonly has three renderings: an authoritative signed PDF, an Akoma Ntoso XML
marked up for machines, and an unofficial HTML reading copy. `legislationLegalValue`
(`AuthoritativeLegalValue` / `DefinitiveLegalValue` / `OfficialLegalValue` /
`UnofficialLegalValue`) is what tells a consumer which text is citable, rather than leaving
them to guess from the file extension.

## What is deliberately out of scope

**Everything inside the text.** schema.org models a law as a `CreativeWork` with parts. It
cannot mark up a clause, a proviso, a definition, an internal cross-reference, or an
amendment instruction such as *"in section 3, delete 'shall' and insert 'must'."*

That is what Akoma Ntoso is for. The split is deliberate and follows SPEC §1.4: **schema.org
carries the bibliographic and relational layer, Akoma Ntoso carries the textual layer**,
joined through `encoding` → `LegislationObject` → `conformsTo` the AKN namespace. Attempting
clause-level structure in schema.org would produce something no legal drafting system can
consume.

## Coupling with `meetings`

`enactedAt` points at the `Meeting` where a law was adopted. Combined with the meeting's
agenda item and its `VoteEvent`, this makes the full chain traversable: **law → sitting →
agenda item → vote → each member's cast vote.** That chain is the reason `code` and
`meetings` are built together rather than in sequence.
