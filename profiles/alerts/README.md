# `alerts` profile — Public warnings and notices

**Status:** implemented · **Depends on:** `_core` · **Standard:** [CAP 1.2](http://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html) (OASIS) · **schema.org:** `SpecialAnnouncement` (projection only)

## Why not `SpecialAnnouncement`

schema.org has the type, and it is the wrong model. Every property on it is pandemic-shaped —
`quarantineGuidelines`, `gettingTestedInfo`, `travelBans`, `schoolClosuresInfo`,
`diseaseSpreadStatistics` — and it carries **no severity, no urgency, no certainty, and no
expiry**. Its `announcementLocation` ranges over `CivicStructure` and `LocalBusiness` only, so
a jurisdiction-wide warning is literally inexpressible.

**CAP** has all of it and is the international standard behind IPAWS in the US, EU-Alert, and
national warning systems worldwide. So CAP is the model; `SpecialAnnouncement` is a discovery
projection and nothing more. This is SPEC §1.4 applied exactly as written.

## Urgency, severity, certainty

These three fields are the reason CAP works. Together they let a receiving system decide
**whether to interrupt someone** — a phone can override silent mode for an immediate, extreme,
observed threat and stay quiet for a future, minor, possible one. Collapsing them into a
single "priority" throws that away.

`responseType` is separate from the free-text `instruction` for the same reason: a machine can
act on `evacuate`, but not on a paragraph.

## Expiry is required

An alert with no expiry stays on screens indefinitely and trains people to ignore alerts. The
validator additionally rejects an alert that expires before it was sent.

## Update and cancel must reference

`messageType` of `update` or `cancel` without `references` leaves consumers showing the old
and new alert side by side. The validator rejects it. The fixtures show a boil-water notice
and the cancel that lifts it, linked by `references` and grouped by `incident`.

## Multilingual by construction

CAP's alert/info split exists so one warning can be issued in several languages at once, and
this profile keeps it. The fixture carries English and Spanish info blocks on a single alert —
one warning, two renderings, not two alerts.

## Geometry is referenced, never embedded

An `AlertArea` carries a human-readable description, a Jurisdiction reference, and a **URL**
to a GeoJSON polygon. A warning polygon is thousands of coordinate pairs, and alerts travel
over constrained channels. This is the first profile to apply the geospatial decision recorded
in [ROADMAP.md](../../ROADMAP.md).

## Alerts and service requests are opposite directions

| | Direction | Profile |
|---|---|---|
| Service request | inbound: resident → government | `requests` |
| Alert | outbound: government → public | `alerts` |

311 is non-emergency by definition. The genuinely ambiguous case is a **service disruption** —
a water main break is both: the disruption is an alert, reports about it are requests.
`ServiceRequest.relatedAlert` links the two.
