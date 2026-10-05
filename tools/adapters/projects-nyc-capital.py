#!/usr/bin/env python3
"""Convert the NYC Capital Projects dataset into the schemaGov projects profile.

Source: NYC Open Data "Capital Projects" (Socrata n7gv-k5yt), published by the Mayor's
Office of Operations: major infrastructure and IT projects of $25M or more that are in
design, procurement or construction.

    python3 tools/adapters/projects-nyc-capital.py --limit 60 --out examples/pilot-nyc-capital

The dataset is a time series: 24 reporting snapshots from 2013-09 to 2023-01, with each
project repeated once per snapshot (pid 101 appears 24 times). Only the LATEST snapshot is
converted. Taking all rows produces one project per row and hundreds of duplicate @ids.
The earlier snapshots hold real history (a forecast completion that slips from 2018 to
2023), which the profile has no way to carry; see the pilot README.

The source publishes no project status and no phase vocabulary of its own beyond a free
text `current_phase`. This adapter therefore does three things on purpose:

  * status is `active` for every record, because the dataset is defined as the set of
    currently active projects. That comes from the dataset's description, not from a column.
  * phase references a scheme DECLARED BY THE PUBLISHER (the values New York uses), not a
    schemaGov scheme. The phases are not the digital-service lifecycle and are not forced
    into it.
  * a phase value that is not a lifecycle phase, or is absent, is omitted and counted.
"""
import argparse
import json
import pathlib
import re
import ssl
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"
HOST = "data.cityofnewyork.us"
DATASET = "n7gv-k5yt"
BASE = f"https://{HOST}/id"
CTX = "https://schema.govfresh.com/v1/context.jsonld"

# Values of current_phase that are real lifecycle stages, in lifecycle order.
PHASES = [
    ("design", "Design", "Design"),
    ("construction-procurement", "Construction Procurement", "Construction Procurement"),
    ("construction", "Construction", "Construction"),
    ("close-out", "Close-Out", "Close-Out"),
]
PHASE_BY_SOURCE = {src: (code, name, i + 1) for i, (code, name, src) in enumerate(PHASES)}


# Official names for the most common agency codes. The source publishes codes only, so these
# are supplied here, not read from the data. Codes not listed keep the code as their name.
AGENCY_NAMES = {
    "DOT": "Department of Transportation",
    "DEP": "Department of Environmental Protection",
    "DDC": "Department of Design and Construction",
    "DPR": "Department of Parks and Recreation",
    "DSNY": "Department of Sanitation",
    "DOE": "Department of Education",
    "NYPD": "New York City Police Department",
    "FDNY": "Fire Department of the City of New York",
    "HPD": "Department of Housing Preservation and Development",
    "DCAS": "Department of Citywide Administrative Services",
    "DOITT": "Department of Information Technology and Telecommunications",
    "DOHMH": "Department of Health and Mental Hygiene",
    "SCA": "School Construction Authority",
    "EDC": "New York City Economic Development Corporation",
}
NOT_AN_AGENCY = {"n/a", "na", "none", ""}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:80]


def write(path, graph):
    path.write_text(json.dumps({"@context": CTX, "@graph": graph}, indent=2,
                               ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--out", default="examples/pilot-nyc-capital")
    args = ap.parse_args()

    latest = fetch(f"https://{HOST}/resource/{DATASET}.json"
                   "?$select=max(date_reported_as_of)")[0]["max_date_reported_as_of"]
    where = urllib.parse.quote(f"date_reported_as_of='{latest}'")
    rows = fetch(f"https://{HOST}/resource/{DATASET}.json"
                 f"?$where={where}&$limit={args.limit}&$order=pid")
    print(f"snapshot reported as of {latest[:10]}")
    gaps, notes = Counter(), Counter()

    juris_id = f"{BASE}/jurisdiction/new-york-city"
    jurisdiction = {"@id": juris_id, "@type": "City", "name": "New York City",
                    "governmentLevel": "municipal",
                    "identifier": [{"@type": "PropertyValue",
                                    "propertyID": "local:socrata-host", "value": HOST}]}

    scheme_id = f"{BASE}/scheme/capital-project-phase"
    scheme = {"@id": scheme_id, "@type": "DefinedTermSet",
              "name": "NYC capital project phase",
              "description": "The values of current_phase in NYC Open Data Capital Projects "
                             "that name a lifecycle stage. Defined by the City of New York, "
                             "not by schemaGov.",
              "hasDefinedTerm": [{"@id": f"{scheme_id}/{c}"} for c, _, _ in PHASES]}
    terms = [{"@id": f"{scheme_id}/{c}", "@type": "DefinedTerm", "termCode": c, "name": n,
              "position": i + 1, "inDefinedTermSet": scheme_id}
             for i, (c, n, _) in enumerate(PHASES)]

    orgs, projects = {}, []

    def agency(code):
        """The source gives one string per agency: a code for most, a name for some. The code
        is kept in its own field (identifier, and alternateName when a name is known). The
        official name comes from AGENCY_NAMES, which this adapter supplies; the source has none."""
        code = code.strip()
        oid = f"{BASE}/organization/{slug(code)}"
        if oid not in orgs:
            known = AGENCY_NAMES.get(code)
            o = {"@id": oid, "@type": "GovernmentOrganization", "name": known or code,
                 "identifier": [{"@type": "PropertyValue",
                                 "propertyID": "local:nyc-agency-code", "value": code}],
                 "organizationClassification": "department", "governmentLevel": "municipal",
                 "areaServed": {"@id": juris_id, "name": "New York City"}}
            if known:
                o["alternateName"] = [code]
            else:
                notes["agency published as a code with no known name; code used as name"] += 1
            orgs[oid] = o
        return {"@id": oid, "name": orgs[oid]["name"]}

    for r in rows:
        pid, name = str(r.get("pid") or "").strip(), (r.get("project_name") or "").strip()
        if not pid or not name:
            gaps["row without pid or project_name"] += 1
            continue
        p = {"@id": f"{BASE}/project/{pid}", "@type": "Project", "name": name,
             "identifier": [{"@type": "PropertyValue",
                             "propertyID": "local:nyc-capital-projects-pid", "value": pid}],
             "status": "active", "dateModified": latest[:10]}
        if r.get("description"):
            p["description"] = re.sub(r"\s+", " ", r["description"]).strip()

        raw = (r.get("current_phase") or "").strip()
        if raw in PHASE_BY_SOURCE:
            p["phase"] = {"@id": f"{scheme_id}/{PHASE_BY_SOURCE[raw][0]}"}
        elif raw:
            gaps[f"phase '{raw}' is not a lifecycle stage; omitted"] += 1
        else:
            gaps["phase blank in source; omitted"] += 1

        start, expected = (r.get("design_start") or "")[:10], (r.get("forecast_completion") or "")[:10]
        if start:
            p["startDate"] = start
        else:
            gaps["design_start blank; startDate omitted"] += 1
        if expected:
            if start and expected < start:
                notes["forecast_completion before design_start; expectedEndDate omitted as inconsistent"] += 1
            else:
                p["expectedEndDate"] = expected
        else:
            gaps["forecast_completion blank; expectedEndDate omitted"] += 1

        managing = (r.get("managing_agency") or "").strip()
        if managing.lower() in NOT_AN_AGENCY:
            if managing:
                gaps["managing_agency is 'n/a'; parentOrganization omitted"] += 1
        else:
            p["parentOrganization"] = agency(managing)
        clients = [c.strip() for c in (r.get("client_agency") or "").split(",")
                   if c.strip().lower() not in NOT_AN_AGENCY]
        members = [agency(c) for c in clients if c != managing]
        if members:
            p["member"] = members
        projects.append(p)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write(out / "jurisdictions.jsonld", [jurisdiction])
    write(out / "organizations.jsonld", list(orgs.values()))
    write(out / "projects.jsonld", [scheme] + terms + projects)

    print(f"{len(projects)} projects, {len(orgs)} agencies -> {out}")
    for label, c in (("source gaps", gaps), ("notes", notes)):
        if c:
            print(f"{label}:")
            for k, v in c.most_common():
                print(f"  {v:4d}  {k}")


if __name__ == "__main__":
    main()
