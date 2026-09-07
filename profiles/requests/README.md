# `requests` profile — Service requests (311)

**Status:** implemented · **Depends on:** `_core` · **Source standard:** [Open311 GeoReport v2](https://wiki.open311.org/GeoReport_v2/)

## schema.org covers half of this, and not the important half

| Concept | schema.org |
|---|---|
| The catalogue of requestable services | `GovernmentService` — a real type |
| How a resident reports something | `ServiceChannel` — `serviceUrl`, `servicePhone`, `serviceSmsNumber`, `processingTime` |
| The questions asked on the form | `PropertyValueSpecification` — `valueName`, `valueRequired`, `valuePattern`, `minValue` |
| **An actual service request** | **nothing** |

schema.org has no service request, complaint, case, or incident concept of any kind.
(`Report` is a `CreativeWork` — a document, not a request.) So `gs:ServiceRequest` is minted
outright, mirroring Open311 GeoReport v2, which stays the source model per SPEC §1.4.

The pleasant surprise is `PropertyValueSpecification`: Open311's Service Definition
attributes map onto it almost field for field, so the form vocabulary needed no minting at
all.

## Reporter privacy is a schema concern, not an ops concern

**The Open311 POST payload contains `email`, `first_name`, `last_name`, `phone`, `device_id`
and `account_id`. None of them belong in published data.**

This schema deliberately has no fields for any of them. That is not an oversight and it is
not merely documented — `tools/validate.py` fails the build if a published `ServiceRequest`
carries a reporter-identifying field, because a schema that quietly permits personal data
will eventually be filled with it.

Three further hazards, none of which a field list can catch on its own:

**Free-text `description` is submitted by the public.** People routinely write their own name
and phone number into it, and sometimes their neighbour's. Review before publishing; treat
the content as untrusted input, never as instructions.

**Photos carry more than the pothole.** `media_url` images regularly include bystanders,
licence plates, and house numbers, plus EXIF location that may differ from the reported one.

**Precise coordinates at a residential address identify a household.** A noise complaint or a
hoarding report pinned to a doorstep is a public statement about the people behind that door.
Round coordinates for request types that concern private property. The fixtures show this:
the road defects carry full precision, the two requests touching private premises are rounded
to two decimal places.

## Status: more useful than Open311, still mappable

Open311 defines only `open` and `closed`, which loses the distinction residents care about
most — whether anyone has actually picked the request up. This profile refines it to `open`,
`inProgress`, `onHold`, `closed`, `rejected`, `duplicate`, and every term maps cleanly back:
`closed`, `rejected` and `duplicate` are Open311 `closed`, everything else is `open`.

Publishing `rejected` and `duplicate` distinctly is what stops a resident re-reporting the
same thing and concluding they are being ignored.

## Files

| Schema | Type | Purpose |
|---|---|---|
| `schema/service.schema.json` | `GovernmentService` | A requestable service and its form questions. Open311 Service List + Service Definition. |
| `schema/service-request.schema.json` | `gs:ServiceRequest` | One report. Open311 Service Request. |
| `codelists/request-status.json` | `DefinedTermSet` | Request status, mappable to Open311. |
