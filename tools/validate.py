#!/usr/bin/env python3
"""Validate gov-schema instance documents.

Two independent checks:

  1. Shape      - each entity against its JSON Schema. Needs `pip install jsonschema`;
                  skipped with a notice if absent.
  2. References - every {"@id": ...} points at an entity that actually exists in the
                  document set, and no entity is declared twice. This is the check that
                  matters most here: the profile forbids inlining copies of entities, so
                  a dangling reference is the characteristic failure mode.

Usage:  python3 tools/validate.py [examples/example-city ...]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "profiles" / "_core" / "schema"
PROFILE_DIRS = [ROOT / "profiles" / d / "schema" for d in ("_core", "org", "code", "meetings", "requests", "budget", "procurement", "catalog", "alerts")]

# @type -> schema file. Roles are validated where they are nested, not standalone.
SCHEMA_FOR = {
    "AdministrativeArea": "jurisdiction.schema.json",
    "Country": "jurisdiction.schema.json",
    "State": "jurisdiction.schema.json",
    "City": "jurisdiction.schema.json",
    "GovernmentOrganization": "organization.schema.json",
    "Person": "person.schema.json",
    "GovernmentBuilding": "facility.schema.json",
    "CityHall": "facility.schema.json",
    "LegislativeBuilding": "facility.schema.json",
    "Courthouse": "facility.schema.json",
    "Embassy": "facility.schema.json",
    "DefenceEstablishment": "facility.schema.json",
    "CivicStructure": "facility.schema.json",
    "EventVenue": "facility.schema.json",
    "Post": "post.schema.json",
    "DataFeed": "directory.schema.json",
    "Legislation": "legislation.schema.json",
    "Meeting": "meeting.schema.json",
    "EventSeries": "meeting.schema.json",
    "ServiceRequest": "service-request.schema.json",
    "GovernmentService": "service.schema.json",
    "Budget": "budget.schema.json",
    "BudgetLine": "budget-line.schema.json",
    "ContractingProcess": "contracting-process.schema.json",
    "Organization": "party.schema.json",
    "PublisherManifest": "manifest.schema.json",
    "DataCatalog": "catalog.schema.json",
    "Dataset": "dataset.schema.json",
    "Alert": "alert.schema.json",
}


def load_graph(paths):
    """Return (entities, sources) for every top-level node across the given files."""
    entities, sources = {}, {}
    dupes = []
    for path in paths:
        doc = json.loads(path.read_text())
        nodes = doc.get("@graph", [doc])
        for node in nodes:
            nid = node.get("@id")
            if not nid:
                continue
            if nid in entities:
                dupes.append((nid, sources[nid], path))
            entities[nid] = node
            sources[nid] = path
    return entities, sources, dupes


def collect_refs(node, path, out):
    """Every {"@id": ...} that is a reference rather than an entity declaration.

    A nested object whose only meaningful key is @id (plus display hints) is a
    reference; a nested object carrying real content is an inline entity.
    """
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "@id":
                continue
            if isinstance(val, dict) and "@id" in val:
                if set(val) <= {"@id", "@type", "name"}:
                    out.append((val["@id"], f"{path}.{key}"))
                else:
                    collect_refs(val, f"{path}.{key}", out)
            else:
                collect_refs(val, f"{path}.{key}", out)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            collect_refs(item, f"{path}[{i}]", out)


def main(argv):
    targets = argv[1:] or ["examples/example-city"]
    paths = []
    for t in targets:
        p = ROOT / t
        paths.extend(sorted(p.glob("**/*.jsonld")) if p.is_dir() else [p])
    if not paths:
        print("no .jsonld files found")
        return 1

    entities, sources, dupes = load_graph(paths)
    errors, notes = [], []

    for nid, first, second in dupes:
        errors.append(f"duplicate @id {nid}\n    declared in {first} and {second}")

    # --- reference integrity -------------------------------------------------
    refs = []
    for nid, node in entities.items():
        collect_refs(node, nid, refs)
    for target, where in refs:
        if target not in entities:
            errors.append(f"dangling reference -> {target}\n    from {where}")

    # --- reporter privacy ----------------------------------------------------
    # Open311's POST payload carries the reporter's name, email, phone, device id
    # and account id. Those fields must not survive into published data. Documenting
    # that is not enough, so it is checked.
    PERSONAL_FIELDS = {
        "email", "telephone", "phone", "mobile",
        "firstname", "first_name", "lastname", "last_name",
        "deviceid", "device_id", "accountid", "account_id",
        "reportername", "reporter_name", "requestorname", "requestor_name",
        "requestername", "requester_name", "submittername", "submitter_name",
        "ipaddress", "ip_address", "reporter", "requestor", "requester", "submitter",
    }
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "ServiceRequest" not in types_:
            continue
        for key in node:
            if key.lower().replace("-", "_").replace("_", "") in {
                f.replace("_", "") for f in PERSONAL_FIELDS
            }:
                errors.append(
                    f"reporter personal data in published request: {nid}\n"
                    f"    field '{key}' identifies the person who reported this. "
                    f"Strip it before publishing."
                )

    # --- budget arithmetic ---------------------------------------------------
    # A budget whose lines do not sum is worse than no budget: it looks
    # authoritative and is wrong. Two things are checked, both of which are
    # arithmetic rather than opinion. Whether a budget balances is NOT checked,
    # because deficit budgets are legitimate.
    def amount_of(node):
        a = node.get("amount") or {}
        return a.get("value"), a.get("currency")

    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]

        # 1. a parent line must equal the sum of its children
        if "BudgetLine" in types_ and node.get("hasPart"):
            parent_val, _ = amount_of(node)
            child_total, missing = 0, False
            for child in node["hasPart"]:
                c = entities.get(child.get("@id"))
                if not c:
                    missing = True
                    break
                cv, _ = amount_of(c)
                if cv is None:
                    missing = True
                    break
                child_total += cv
            if not missing and parent_val is not None and child_total != parent_val:
                errors.append(
                    f"budget line does not equal the sum of its parts: {nid}\n"
                    f"    parent {parent_val:,} but children total {child_total:,} "
                    f"(difference {parent_val - child_total:,})"
                )

        # 2. every line must use its budget's currency
        if "BudgetLine" in types_:
            _, cur = amount_of(node)
            b = entities.get((node.get("budget") or {}).get("@id"))
            if b and cur and b.get("currency") and cur != b["currency"]:
                errors.append(
                    f"currency mismatch: {nid}\n"
                    f"    line is {cur} but budget {b['@id']} is {b['currency']}"
                )

    # --- procurement integrity -----------------------------------------------
    # Contract data that does not tie together cannot be audited, and the specific
    # ways it fails to tie together are well known.
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "ContractingProcess" not in types_:
            continue

        awards = {a.get("awardId"): a for a in node.get("award", [])}
        party_ids = {p.get("@id") for p in node.get("party", [])}

        for contract in node.get("contract", []):
            aid = contract.get("awardId")

            # 1. every contract must trace to an award in the same process
            if aid not in awards:
                errors.append(
                    f"contract references an unknown award: {nid}\n"
                    f"    contract {contract.get('contractId')} cites awardId "
                    f"'{aid}', which is not an award in this process"
                )
                continue

            # 2. a contract worth more than its award is an unrecorded variation
            av = (awards[aid].get("value") or {}).get("value")
            cv = (contract.get("value") or {}).get("value")
            if av is not None and cv is not None and cv > av:
                errors.append(
                    f"contract exceeds its award: {nid}\n"
                    f"    contract {contract.get('contractId')} is {cv:,} but award "
                    f"{aid} is {av:,}. Record the variation on the award."
                )

            # 3. paying more than the contract is worth
            pv = (contract.get("amountPaid") or {}).get("value")
            if cv is not None and pv is not None and pv > cv:
                errors.append(
                    f"amount paid exceeds contract value: {nid}\n"
                    f"    contract {contract.get('contractId')} paid {pv:,} "
                    f"against a value of {cv:,}"
                )

        # 4. a supplier must be a declared party, or it cannot be joined to anything
        for award in node.get("award", []):
            for sup in award.get("supplier", []):
                if sup.get("@id") not in party_ids:
                    errors.append(
                        f"supplier is not a declared party: {nid}\n"
                        f"    award {award.get('awardId')} names {sup.get('@id')}, "
                        f"which is absent from this process's party list"
                    )

    # --- shape ---------------------------------------------------------------
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        # Register every schema under its $id so that relative $refs resolve the
        # way they will once published, not the way the repo happens to be laid out.
        resources = []
        for d in PROFILE_DIRS:
            for f in d.glob("*.schema.json"):
                contents = json.loads(f.read_text())
                resources.append((contents["$id"], Resource.from_contents(contents)))
        registry = Registry().with_resources(resources)

        checked = 0
        for nid, node in entities.items():
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            name = next((SCHEMA_FOR[t] for t in types if t in SCHEMA_FOR), None)
            if not name:
                notes.append(f"no schema mapped for @type {types} ({nid})")
                continue
            base = next(d for d in PROFILE_DIRS if (d / name).exists())
            schema = json.loads((base / name).read_text())
            # format is annotation-only by default; dates and IRIs matter here.
            v = Draft202012Validator(
                schema,
                registry=registry,
                format_checker=Draft202012Validator.FORMAT_CHECKER,
            )
            for e in sorted(v.iter_errors(node), key=lambda e: list(e.path)):
                loc = "/".join(str(x) for x in e.path) or "(root)"
                errors.append(f"{nid}\n    {loc}: {e.message}")
            checked += 1
        notes.append(f"shape-checked {checked} entities against {len(SCHEMA_FOR)} schemas")
    except ImportError:
        notes.append("shape check SKIPPED - pip install jsonschema referencing")

    # --- alerts ---------------------------------------------------------------
    # A malformed warning is worse than no warning: it either fails to reach people
    # or fails to stop reaching them.
    from datetime import datetime

    def parse_dt(v):
        try:
            return datetime.fromisoformat(str(v))
        except (ValueError, TypeError):
            return None

    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "Alert" not in types_:
            continue

        if node.get("messageType") in ("update", "cancel") and not node.get("references"):
            errors.append(
                f"alert '{node.get('messageType')}' does not reference what it supersedes: {nid}\n"
                f"    without references, consumers show the old and new alert side by side"
            )

        sent = parse_dt(node.get("sent"))
        for info in node.get("alertInfo", []):
            expires = parse_dt(info.get("expires"))
            if sent and expires and expires <= sent:
                errors.append(
                    f"alert expires before it was sent: {nid}\n"
                    f"    sent {node.get('sent')}, expires {info.get('expires')} "
                    f"({info.get('inLanguage')})"
                )

    # --- service request status history ---------------------------------------
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "ServiceRequest" not in types_:
            continue

        history = node.get("statusHistory") or []
        dates = [parse_dt(h.get("date")) for h in history]
        if any(d is None for d in dates):
            pass
        elif dates != sorted(dates):
            errors.append(
                f"status history is not in chronological order: {nid}"
            )
        if history and history[-1].get("requestStatus") != node.get("requestStatus"):
            errors.append(
                f"status history disagrees with current status: {nid}\n"
                f"    request is '{node.get('requestStatus')}' but history ends at "
                f"'{history[-1].get('requestStatus')}'"
            )
        if node.get("requestStatus") == "duplicate" and not node.get("duplicateOf"):
            errors.append(
                f"request marked duplicate without saying of what: {nid}\n"
                f"    set duplicateOf; a status note naming the other request cannot be followed"
            )

    # --- discovery manifest ---------------------------------------------------
    # The manifest is the routing table. A duplicate or misplaced entry makes a
    # publisher's data undiscoverable in a way nothing else surfaces.
    for nid, node in entities.items():
        types_ = node.get("@type")
        types_ = types_ if isinstance(types_, list) else [types_]
        if "PublisherManifest" not in types_:
            continue

        if "/.well-known/gov-schema.json" not in nid:
            errors.append(
                f"manifest is not at its conventional location: {nid}\n"
                f"    serve it at /.well-known/gov-schema.json (RFC 8615), or consumers "
                f"cannot find it without being told the URL"
            )

        seen = {}
        for ep in node.get("profileEndpoint", []):
            prof = ep.get("profile")
            if prof in seen:
                errors.append(
                    f"manifest declares '{prof}' twice: {nid}\n"
                    f"    {seen[prof]} and {ep.get('url')} - a routing table needs one "
                    f"entry per profile"
                )
            seen[prof] = ep.get("url")

    # --- conformance levels ---------------------------------------------------
    # SPEC section 4 defines three levels; documents declare one with conformanceLevel.
    # An unverified claim is worse than no claim, so every declaration is checked.
    JURISDICTION_TYPES = {"AdministrativeArea", "Country", "State", "City"}

    def types_of(node):
        v = node.get("@type")
        return set(v if isinstance(v, list) else [v])

    claims = [
        (nid, lvl)
        for nid, node in entities.items()
        for lvl in (node.get("conformanceLevel") or [])
    ]

    if claims:
        jurisdictions = [n for n in entities.values() if types_of(n) & JURISDICTION_TYPES]
        orgs = [n for n in entities.values() if "GovernmentOrganization" in types_of(n)]
        conflated = [
            n["@id"] for n in entities.values()
            if "GovernmentOrganization" in types_of(n) and types_of(n) & JURISDICTION_TYPES
        ]
        unidentified = [
            n["@id"] for n in jurisdictions + orgs if not n.get("identifier")
        ]

        core_failures = []
        if not jurisdictions:
            core_failures.append("no Jurisdiction present")
        if not orgs:
            core_failures.append("no GovernmentOrganization present")
        for c in conflated:
            core_failures.append(f"{c} is typed as both a Jurisdiction and an Organization")
        for u in unidentified:
            core_failures.append(f"{u} carries no identifier")

        # errors accumulated so far are the Standard criterion
        pre_conformance_errors = len(errors)

        for nid, lvl in claims:
            if lvl not in ("core", "standard", "extended"):
                errors.append(f"unknown conformance level '{lvl}' claimed by {nid}")
                continue
            for f in core_failures:
                errors.append(f"conformance: {nid} claims '{lvl}' but Core is not met\n    {f}")
            if lvl in ("standard", "extended") and pre_conformance_errors:
                errors.append(
                    f"conformance: {nid} claims '{lvl}', which requires a clean document set\n"
                    f"    {pre_conformance_errors} error(s) above must be resolved first"
                )
            if lvl in ("standard", "extended"):
                # Requirements enforced at Standard rather than in the schema, so that
                # real-world data can still be represented at Core.
                for oid, o in entities.items():
                    ot = o.get("@type")
                    ot = ot if isinstance(ot, list) else [ot]
                    if "GovernmentOrganization" in ot and not o.get("areaServed"):
                        errors.append(
                            f"conformance: {nid} claims '{lvl}' but {oid}\n"
                            f"    has no areaServed. Standard requires every organization to be "
                            f"placed in the territorial hierarchy."
                        )
                    if "ContractingProcess" in ot:
                        tn = o.get("tender") or {}
                        if tn and not tn.get("procurementMethod"):
                            errors.append(
                                f"conformance: {nid} claims '{lvl}' but {oid}\n"
                                f"    has a tender with no procurementMethod. Standard requires it, "
                                f"so that non-competitive awards remain visible."
                            )
            if lvl == "extended":
                node = entities[nid]
                if not (node.get("distribution") or node.get("sourceDataset")):
                    errors.append(
                        f"conformance: {nid} claims 'extended' but provides no machine-readable\n"
                        f"    link to its source standard (distribution or sourceDataset)"
                    )

    # --- report --------------------------------------------------------------
    print(f"gov-schema validate: {len(paths)} file(s), {len(entities)} entities, "
          f"{len(refs)} cross-references")
    if claims:
        shown = ", ".join(sorted({lvl for _, lvl in claims}))
        print(f"  note: conformance claimed ({len(claims)} declaration(s)): {shown}")
    for n in notes:
        print(f"  note: {n}")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK - all references resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
