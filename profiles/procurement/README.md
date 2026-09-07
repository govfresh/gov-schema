# `procurement` profile — Procurement and contracts

**Status:** implemented · **Depends on:** `_core`, `budget` · **Source standard:** [OCDS](https://standard.open-contracting.org)

## schema.org has nothing usable

No tender, procurement, bid, or solicitation concept exists. The word *contract* appears only
as `GeneralContractor` and `RoofingContractor` — business categories — and `award` means a
prize or credential.

`Demand` and `Offer` look promising until you read them: they carry `gtin`, `sku`,
`itemCondition`, `warranty`, `inventoryLevel`. They are retail constructs, and forcing a
public tender into them imports semantics that do not apply while gaining nothing. So this
profile mints its own types over the **Open Contracting Data Standard**, which is used in
more than fifty countries and stays the source model per SPEC §1.4.

## The ocid is the whole point

Everything hangs off one identifier, the Open Contracting ID. That is what lets a single
purchase be followed from the budget line that funded it, through the tender, the award, the
contract, and the payments — and what makes data from different publishers aggregatable.

```
BudgetLine ──budgetLine──→ ContractingProcess ──tender──→ Tender
                                  │
                                  ├──award──→ Award ──supplier──→ Party
                                  └──contract──→ Contract (awardId → Award)
```

## Suppliers are references, never names

A supplier recorded as free text cannot be joined across contracts, to a company register, or
to a register of interests. That is not a minor data-quality issue — **unjoinable supplier
data is the main reason procurement transparency fails in practice**, because repeat awards
to connected parties stay invisible when every contract spells the name differently.

`Party` therefore requires at least one scheme-qualified identifier: an
[org-id.guide](https://org-id.guide) prefix for the national company register
(`org-id:GB-COH`, `org-id:US-EIN`) or an LEI. This is the same `propertyID`/`value` pattern
`_core` established, and the same one OCDS uses, so it crosswalks without transformation.

Government participants are **not** duplicated as parties. The buyer and procuring entity are
`_core` `GovernmentOrganization`s referenced directly, so one body never becomes two entities.

## Method and rationale make non-competitive awards visible

`procurementMethod` is required. Publishing it consistently is what lets anyone ask *how much
of this government's spending was never competed* — a question that is otherwise unanswerable
no matter how many contracts are published.

When the method is `direct`, `procurementMethodRationale` is expected. A sole-source award
with no stated reason is the most common audit finding in public procurement. The fixtures
include one: an emergency structural assessment, with the statutory authority cited.

`numberOfTenderers` matters for the same reason — a competitive method that attracted one bid
is not a competition, and only that field reveals it.

## Three values, deliberately distinct

Tender estimate, award value, contract value, and amount paid are four different numbers, and
collapsing them hides exactly what an auditor is looking for. The validator enforces the
relationships:

- every contract must cite an `awardId` that exists in the same process
- a contract worth more than its award is an unrecorded variation
- paying more than the contract value is flagged
- a supplier named in an award must be a declared party

## Coupling to `budget`

`budgetLine` links a process to the appropriation that funds it — which is why `procurement`
was built after `budget`. Combined with the earlier profiles, the full chain runs:

**appropriation ordinance → council vote → budget line → contracting process → award → supplier.**
