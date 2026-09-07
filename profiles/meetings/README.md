# `meetings` profile — Meetings, agendas, and votes

**Status:** implemented · **Depends on:** `_core`, `code` · **Source standard:** [Popolo](https://www.popoloproject.com), Open Civic Data

## What schema.org gives free

`Event` covers scheduling almost completely, and this profile changes none of it:

- `eventSchedule` → `Schedule` with `byDay`, `byMonthWeek`, `repeatFrequency`, `exceptDate`,
  `scheduleTimezone`. *"Second Wednesday of each month"* is `byDay: Wednesday`,
  `byMonthWeek: 2`, `repeatFrequency: P1M` — machine-readable, unlike a prose string.
- `eventStatus` → `EventScheduled` / `EventCancelled` / `EventPostponed` / `EventRescheduled`
  / `EventMovedOnline`. A cancelled meeting stays published as cancelled; it does not vanish.
- `eventAttendanceMode` → offline, online, or mixed — hybrid meetings are the norm now.
- `superEvent` / `subEvent` for the series-to-sitting relationship.

## What had to be minted, and why

**`gs:Meeting`** — `Event` cannot distinguish a council meeting from a summer concert, and
discovery depends on that distinction. Everything else is inherited from `Event` unchanged.

**`gs:AgendaItem`** — `ListItem` supplies ordering via `position`; this adds the decision and
the link to the legislation considered.

**`gs:VoteEvent` and `gs:Vote`** — schema.org has `VoteAction`, but it is built around
*choosing a candidate*: its `candidate` property ranges over `Person`. There is no way to
express aye, nay, or abstain on a motion. So this follows Popolo's `VoteEvent` / `Count` /
`Vote` model instead, which was designed for exactly this and is used by parliamentary
monitoring organisations worldwide.

## Vote records

Publishing the tally alone is valid. Publishing individual votes is what makes a record
auditable, and it is the difference between *"the motion carried 3–1"* and *"you can see how
your councilmember voted."*

`requiredMajority` matters more than it looks: without it a reader cannot tell whether a 4–3
vote carried, because the threshold varies by motion type and jurisdiction.

Absence is distinguished from abstention throughout, because they mean different things — an
abstention is a decision, an absence is not — and several systems count them differently
against a required majority.

## The join to `code`

An agenda item's `about` points at the `Legislation` under consideration, and the law's
`enactedAt` points back at the meeting. That closes the loop:

```
Legislation ──enactedAt──→ Meeting ──agendaItem──→ AgendaItem ──voteEvent──→ VoteEvent
     ↑                                                  │                        │
     └────────────────── about ─────────────────────────┘                      vote
                                                                                 │
                                                                        Person (voter)
```

Building these profiles separately would have produced two halves that could not express
this chain, which is why they were specified together.
