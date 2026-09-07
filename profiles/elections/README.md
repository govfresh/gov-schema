# `elections` profile — Elections and results

**Status:** implemented · **Depends on:** `_core`, `org` · **Standard:** NIST SP 1500-100, VIP · **schema.org:** `PoliticalParty` only

## schema.org has nothing here

No `Election`, no `Candidate`, no `Ballot`, no constituency — the concepts do not exist in the
vocabulary. The single reusable type is `PoliticalParty`, and it is used unchanged.

## The loop this closes

The `org` profile records that a Post is filled by election and how long a term runs, but
nothing about **the election that produced the officeholder**. That gap is now closed:

```
Election ──contest──→ Contest ──post──→ Post ──(Role)──→ Person
                          └──candidacy──→ Candidacy ──candidate──→ Person
```

A contest for an office must say which Post it fills — the validator enforces it — so a
result can be traced to the office, and the office to the person who then held it. The
fixtures show the 2022 general election electing the sitting mayor and the District 2
councilmember, and a scheduled special election for the District 5 seat that the `org`
profile records as vacant.

## `electoralSystem` is what makes this travel

Required on every contest, because **a result cannot be interpreted without it**. Forty per
cent of the vote wins outright under first-past-the-post, triggers a runoff under a two-round
system, and yields a proportion of seats under a party list. A profile that assumed one system
would only work in the country it was written in.

Ten systems are enumerated: FPTP, block vote, two-round, party list, STV, MMP, parallel,
ranked choice, approval, and indirect. This is the elections equivalent of what COFOG does for
`budget` — the field that lets data from different countries sit side by side.

## Candidacy, not candidate

The same person may stand in several contests, and their party affiliation, ballot position
and result belong to **the standing**, not to them. `candidate` is a reference, so someone who
stands and then takes office is the same entity in `elections` and in `org`.

`ballotName` is separate from the person's name because what appears on a ballot frequently
is not someone's full legal name.

## Distinctions that change the arithmetic

**Withdrawn and disqualified are not the same as losing.** A candidate who never faced the
voters is different from one who did and lost, and conflating them distorts every share
computed from the result. Withdrawn and disqualified candidacies are excluded from the vote
total the validator reconciles.

**Invalid votes are reported separately.** Spoiled and blank ballots are a real signal, and
folding them into the total makes every share slightly wrong.

**Turnout is not stored.** `registeredVoters` and `ballotsCast` are, because publishing a
derived percentage loses the ability to recompute it against a corrected register.

## Arithmetic is checked

Election returns that do not add up are the classic sign of a transcription error, and every
share published from them is wrong. The validator enforces:

- candidacy and ballot-option counts sum to `validVotes`
- `validVotes` + `invalidVotes` equals `totalVotes`
- no more candidates elected than there are seats
- an office contest names the Post it fills
- a ballot measure carries options, not candidates

## Out of scope

Individual voter records, the electoral register, and anything identifying how a person voted.
This profile describes contests and aggregate results only.
