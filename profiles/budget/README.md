# `budget` profile — Budgets and spending

**Status:** implemented · **Depends on:** `_core`, `code`, `meetings` · **Source standard:** [Fiscal Data Package](https://specs.frictionlessdata.io/fiscal-data-package/), [COFOG](https://unstats.un.org/unsd/classifications/Family/Detail/4), [GFSM 2014](https://www.imf.org/external/pubs/ft/gfs/manual/2014/gfsfinal.pdf)

## schema.org has nothing here

No budget, no fiscal, no expenditure, no appropriation — the words do not appear in the
vocabulary. `MonetaryAmount` is a value type (a number and a currency), not a model, and
`MonetaryGrant` is about grants awarded, not money appropriated.

So this profile mints `gs:Budget` and `gs:BudgetLine` outright and mirrors the **Fiscal Data
Package**, which stays the source model per SPEC §1.4. Publish the FDP itself in
`distribution`; this projection exists for discovery and for joining the budget to the
organization, meeting, and legislation that produced it.

## Budget phase is the field everyone omits

**A budget figure without its phase is not comparable to any other figure.** Proposed,
approved, adjusted, and executed are four different numbers for the same line, and a
publisher who ships "the budget" without saying which one has published something that cannot
be used.

`budgetPhase` is therefore required on every Budget. `supersedes` links a phase to the one it
revises, and both are retained — comparing a proposal against what was actually approved, and
approved against what was actually spent, is most of what budget transparency is for.

## Direction, and why a bare amount is useless

Every line is `revenue`, `expenditure`, or `financing`. Without it an amount cannot be
interpreted at all: 41,200,000 is meaningless until you know whether it is money coming in or
going out. Required, no default.

## Three classifications, doing different jobs

| Dimension | Standard | Answers |
|---|---|---|
| `functionalClassification` | **COFOG** (UN) | *What is the money for?* Health, education, public order. |
| `economicClassification` | **GFSM 2014** (IMF) | *What kind of transaction?* Salaries, goods, interest, capital. |
| `administrativeClassification` | a `GovernmentOrganization` reference | *Who spends it?* |

COFOG is the one that makes this profile work internationally. Administrative structures
differ in every country and department names do not translate, but *"how much goes to health"*
is answerable anywhere. Both COFOG and GFSM are hierarchical: only the top level is
enumerated, and publishers may use full subcodes such as `04.5` or `07.3.1` as the value.

`administrativeClassification` points at an organization rather than carrying a department
name as text, so budget lines join directly to the `org` profile.

## Currency is required on every amount

Not inherited from the budget. Amounts get copied out of their document, and a figure that
silently assumes a currency is exactly how conversion errors happen. The validator rejects a
line whose currency differs from its budget's.

## Arithmetic is checked

`tools/validate.py` enforces two things that are arithmetic rather than opinion:

- a parent line must equal the sum of its `hasPart` children
- every line must use its budget's currency

It does **not** check whether the budget balances, because deficit budgets are legitimate.

## Coupling

`enactedAt` → the `Meeting` that adopted it; `legislation` → the appropriation ordinance in
the `code` profile. Combined with the meetings profile's vote records, the chain runs:
**budget → appropriation ordinance → meeting → agenda item → vote → each member's vote.**
