# Invalid fixtures

`projects.jsonld` is wrong on purpose: twelve nodes, each with one fault, covering unknown
status, malformed date, phase given as text, a milestone with no name or project, dates in the
wrong order, a dangling reference, and references to the wrong kind of thing (an organization as
a phase, a place as the responsible organization).

`python3 tools/check-invalid.py` (`npm run validate:invalid`) runs the validators over it and
fails unless every fault is flagged and the two clean nodes are not. Passing data proves
nothing if a validator accepts everything.

Nothing here is published, and the JSON-LD audit skips it.
