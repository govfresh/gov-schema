#!/usr/bin/env python3
"""Convert GOV.UK Service Standard assessment reports into the schemaGov projects profile.

Source: the GOV.UK Search API (document type service_standard_report) and, per report, the
Content API. A report records one assessment of one digital service at one stage.

    python3 tools/adapters/projects-govuk-assessments.py --out examples/pilot-govuk-assessments

What the feed is, and is not. It is evidence about services, not a project list. There is no
service identifier, no project status and no organization field for the department that owns
the service (the `organisations` metadata is always GDS, the publisher). So:

  * A SERVICE is recovered by following the "Previous assessment reports" links inside each
    report, grouping reports into chains. Titles are inconsistent ("HO View or share your DBS
    result beta assessment report" next to "Register a birth") and cannot be used.
  * The owning department is the "Service provider" row in the report's own table. That is
    free text ("DWP", "Department for Work and Pensions"), so it is resolved against the
    GOV.UK organisations register (/api/organisations): an exact match on official title or
    abbreviation gives the register's own record, with the same @id the services pilot uses.
    A name the register does not match exactly stays as written and is counted.
  * PHASE is the stage of the latest assessment. An assessment is held to decide whether a
    service may leave a stage, so a service assessed at alpha was in alpha on that date. What
    came after is unknown, and `dateModified` carries the assessment date for that reason.
  * No STATUS is published, so none is asserted.
  * Each assessment is a Milestone and an Article about the project, using the same report.
  * Result mapping (a judgement, not a GDS rule): met/green -> met, amber -> partiallyMet,
    not-met/red -> notMet.
"""
import argparse
import html
import json
import pathlib
import re
import ssl
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

UA = "schemaGov-adapter/1.0 (schema.govfresh.com)"
SITE = "https://www.gov.uk"
BASE = f"{SITE}/id"
CTX = "https://schema.govfresh.com/v1/context.jsonld"
DS = "https://schema.govfresh.com/v1/dsphase/"
STAGES = ("discovery", "alpha", "beta", "live")
RESULT = {"met": "met", "green": "met", "amber": "partiallyMet", "not-met": "notMet",
          "not met": "notMet", "red": "notMet"}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(1 + i)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:80]


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")).strip()


def table_value(body, label):
    m = re.search(rf"<td>\s*{label}\s*:?\s*</td>\s*<td>(.*?)</td>", body, re.I | re.S)
    return clean(m.group(1)) if m else ""


def parse_date(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def stage_of(*texts):
    for t in texts:
        t = (t or "").lower()
        for st in STAGES:
            if re.search(rf"\b{st}\b", t):
                return st
    return None


def kind_of(*texts):
    t = " ".join(x or "" for x in texts).lower()
    if "reassess" in t:
        return "reassessment"
    if "review" in t:
        return "review"
    return "assessment"


def service_name(body):
    """The service name is the first paragraph after the 'Service Standard assessment report' line."""
    paras = [clean(p) for p in re.findall(r"<p>(.*?)</p>", body, re.S)]
    paras = [p for p in paras if p and not re.match(r"service standard (assessment )?report", p, re.I)]
    return paras[0] if paras else ""


def previous_links(body):
    m = re.search(r'id="previous-assessment-reports"(.*?)(?:<h2|$)', body, re.S)
    if not m:
        return []
    return re.findall(r"service-standard-reports/([a-z0-9\-]+)", m.group(1))


def usable(name):
    """Reject text that is not a service name: a heading, a sentence, or generic wording."""
    n = (name or "").strip(" -\u2013\u2014")
    if not n or len(n) > 100 or n[-1] in ".:":
        return False
    return not re.search(r"previous assessment|^assessment date|^(digital )?service standard|assessment report|"
                         r"^this\b|^the service\b", n, re.I)


def title_name(title):
    t = re.sub(r"\s*\b(alpha|beta|live|discovery|(re)?assessment)\b.*$", "", title, flags=re.I)
    return t.strip(" -\u2013\u2014")


def best_name(reps):
    """Newest report first: the body's service name, then the title with the assessment
    wording removed. Both are tried on every report before giving up."""
    for r in reversed(reps):
        for cand in (r["name"], title_name(r["title"])):
            if usable(cand):
                return cand.strip(" -\u2013\u2014")
    return ""


def load_register():
    """GOV.UK's own list of government bodies. Returns (by_name, by_abbreviation).

    A name that matches more than one live body is ambiguous, so it is not resolved.
    """
    orgs, url = [], f"{SITE}/api/organisations"
    while url:
        page = fetch(url)
        if not page:
            break
        orgs += page["results"]
        url = page.get("next_page_url")
    by_name, by_abbr = defaultdict(list), defaultdict(list)
    for o in orgs:
        d = o.get("details") or {}
        live = d.get("govuk_status") == "live"
        rec = {"title": o["title"], "abbr": d.get("abbreviation"), "content_id": d.get("content_id"),
               "url": o.get("web_url"), "live": live}
        if not rec["content_id"]:
            continue
        by_name[norm_name(o["title"])].append(rec)
        if rec["abbr"]:
            by_abbr[norm_name(rec["abbr"])].append(rec)
    return by_name, by_abbr


def norm_name(s):
    """Spelling variants that never change which body is meant: case, spacing, '&' for 'and',
    a leading 'the', curly quotes. Nothing fuzzier than that: 'Department for Works and
    Pensions' is a typo a person can see and a program should not guess at."""
    t = (s or "").replace("\xa0", " ").replace("\u2019", "'").replace("&", " and ")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return re.sub(r"^the ", "", t)


def lookup(text, register):
    by_name, by_abbr = register
    for index in (by_name, by_abbr):
        hits = index.get(norm_name(text), [])
        live = [h for h in hits if h["live"]]
        hits = live or hits
        if len(hits) == 1:
            return hits[0]
    return None


def resolve(text, register):
    hit = lookup(text, register)
    if hit:
        return hit
    # "Department for Work and Pensions (DWP)": accept the bracket only when it is the
    # register's own abbreviation for the body named before it.
    m = re.match(r"^(.*?)\s*\(([^()]{2,12})\)\s*$", text or "")
    if m:
        hit = lookup(m.group(1), register)
        if hit and hit["abbr"] and norm_name(hit["abbr"]) == norm_name(m.group(2)):
            return hit
    return None


def write(path, graph):
    path.write_text(json.dumps({"@context": CTX, "@graph": graph}, indent=2, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="examples/pilot-govuk-assessments")
    ap.add_argument("--max", type=int, default=600)
    args = ap.parse_args()
    gaps, notes = Counter(), Counter()

    listing = []
    for start in range(0, args.max, 100):
        q = ("filter_format=service_standard_report&count=100&start=%d&order=-public_timestamp"
             "&fields=title,link,public_timestamp,assessment_date,stage,result" % start)
        page = fetch(f"{SITE}/api/search.json?{q}")
        if not page or not page["results"]:
            break
        listing += page["results"]
    print(f"{len(listing)} reports listed")

    def get(r):
        s = r["link"].rsplit("/", 1)[-1]
        d = fetch(f"{SITE}/api/content/service-standard-reports/{s}")
        return s, r, (d or {}).get("details", {}).get("body", "")

    with ThreadPoolExecutor(6) as ex:
        fetched = list(ex.map(get, listing))

    reports = {}
    for s, r, body in fetched:
        if not body:
            gaps["report body unavailable; skipped"] += 1
            continue
        date = r.get("assessment_date") or parse_date(table_value(body, "Assessment date"))
        stage = stage_of(r.get("stage"), table_value(body, "Stage"), r["title"])
        reports[s] = {
            "slug": s, "title": clean(r["title"]), "published": (r.get("public_timestamp") or "")[:10],
            "date": date, "stage": stage,
            "kind": kind_of(r.get("stage"), table_value(body, "Stage"), r["title"]),
            "result": (r.get("result") or table_value(body, "Result") or "").strip().lower(),
            "provider": table_value(body, "Service provider"),
            "name": service_name(body), "previous": previous_links(body),
        }

    # group reports into services by following "previous assessment" links
    parent = {s: s for s in reports}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for s, rep in reports.items():
        for p in rep["previous"]:
            parent[find(p)] = find(s)
    groups = defaultdict(list)
    for s in reports:
        groups[find(s)].append(s)
    for g in groups.values():  # links to reports outside the feed would be orphans
        pass

    jurisdiction_id = f"{BASE}/jurisdiction/gb"
    jurisdiction = {"@id": jurisdiction_id, "@type": "Country", "name": "United Kingdom",
                    "governmentLevel": "national",
                    "identifier": [{"@type": "PropertyValue", "propertyID": "iso3166-1-alpha2", "value": "GB"}]}
    orgs = {}

    register = load_register()
    print(f"{sum(len(v) for v in register[0].values())} bodies in the GOV.UK register")

    def org(text):
        """Resolve the written name against the register; keep it as written if no match."""
        hit = resolve(text, register)
        if hit:
            oid = f"{BASE}/organization/{slug(hit['content_id'])}"
            if oid not in orgs:
                alt = sorted({a for a in (hit["abbr"], text) if a and a != hit["title"]})
                o = {"@id": oid, "@type": "GovernmentOrganization", "name": hit["title"],
                     "identifier": [{"@type": "PropertyValue", "propertyID": "local:govuk-content-id",
                                     "value": hit["content_id"]}],
                     "organizationClassification": "department", "governmentLevel": "national",
                     "areaServed": {"@id": jurisdiction_id, "name": "United Kingdom"},
                     "sameAs": [hit["url"]]}
                if alt:
                    o["alternateName"] = alt
                orgs[oid] = o
            elif text != orgs[oid]["name"] and text not in orgs[oid].get("alternateName", []):
                orgs[oid].setdefault("alternateName", []).append(text)
            notes["provider resolved against the GOV.UK register"] += 1
            return {"@id": oid, "name": orgs[oid]["name"]}
        gaps["provider not matched exactly in the register; kept as written"] += 1
        oid = f"{BASE}/organization/{slug(text)}"
        orgs.setdefault(oid, {"@id": oid, "@type": "GovernmentOrganization", "name": text,
                              "identifier": [{"@type": "PropertyValue",
                                              "propertyID": "local:govuk-service-provider", "value": text}],
                              "organizationClassification": "department", "governmentLevel": "national",
                              "areaServed": {"@id": jurisdiction_id, "name": "United Kingdom"}})
        return {"@id": oid, "name": text}

    gds = org("Government Digital Service")
    projects, milestones, articles = [], [], []
    for members in groups.values():
        reps = sorted((reports[s] for s in members if s in reports),
                      key=lambda r: (r["date"] or "", r["published"]))
        if not reps:
            gaps["group with no fetched report"] += 1
            continue
        first, latest = reps[0], reps[-1]
        pid = f"{BASE}/project/{first['slug']}"
        name = best_name(reps)
        if not name:
            gaps["no usable service name in any report; latest title used"] += 1
            name = latest["title"]
        p = {"@id": pid, "@type": "Project", "name": name}
        if latest["stage"]:
            p["phase"] = {"@id": DS + latest["stage"]}
        else:
            gaps["no stage on latest report; phase omitted"] += 1
        if latest["date"]:
            p["dateModified"] = latest["date"]
        if latest["provider"]:
            p["parentOrganization"] = org(latest["provider"])
        else:
            gaps["no service provider; parentOrganization omitted"] += 1
        projects.append(p)

        for r in reps:
            label = f"{(r['stage'] or 'service').capitalize()} {r['kind']}"
            m = {"@id": f"{pid}/milestone/{r['slug']}", "@type": "Milestone", "name": label,
                 "about": {"@id": pid}, "url": f"{SITE}/service-standard-reports/{r['slug']}"}
            status = RESULT.get(r["result"])
            if status:
                m["status"] = status
            else:
                gaps[f"result '{r['result'] or 'blank'}' not mapped; milestone status omitted"] += 1
            if r["date"]:
                m["dueDate"] = r["date"]
                if status in ("met", "partiallyMet"):
                    m["dateMet"] = r["date"]
            else:
                gaps["assessment date missing"] += 1
            milestones.append(m)
            a = {"@id": f"{pid}/update/{r['slug']}", "@type": "Article", "name": r["title"],
                 "url": f"{SITE}/service-standard-reports/{r['slug']}", "about": {"@id": pid},
                 "publisher": gds}
            if r["published"]:
                a["datePublished"] = r["published"]
            articles.append(a)

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write(out / "jurisdictions.jsonld", [jurisdiction])
    write(out / "organizations.jsonld", list(orgs.values()))
    write(out / "projects.jsonld", projects + milestones + articles)
    sizes = Counter(len(g) for g in groups.values())
    print(f"{len(projects)} services, {len(milestones)} assessments, {len(orgs)} organizations -> {out}")
    print("reports per service:", dict(sorted(sizes.items())))
    for label, c in (("source gaps", gaps), ("notes", notes)):
        if c:
            print(f"{label}:")
            for k, v in c.most_common():
                print(f"  {v:4d}  {k}")


if __name__ == "__main__":
    main()
