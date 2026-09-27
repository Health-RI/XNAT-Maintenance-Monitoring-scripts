# Scratchpad

## users_per_project: disabled users are silently omitted

Found while validating the new `test-environment/` against a real XNAT 1.9.3.1.

`project.users` in xnatpy is backed by `/data/users`, which only returns
**enabled** accounts. Disabled users that still hold a project role therefore
never appear in the CSV.

In the test fixtures this hides two users:
* `d.disabled` (member of TESTPROJ02)
* `h.disabled.owner` (the *only* owner of TESTPROJ03)

TESTPROJ03 consequently looks like it has no owner at all, which is misleading
for an access-review report -- a disabled account retaining owner rights is
exactly what such a review should flag.

`/xapi/users` does return disabled accounts, so a fix could cross-reference
that endpoint and add an `enabled` column. Worth deciding whether the report
should list disabled users or explicitly exclude them.

## users_per_project: projects are matched on name, not ID

`--project` compares against `project.name` (the display name), not the project
ID. `--project TESTPROJ01` yields nothing; you have to pass
`--project "Cardiac Imaging Study"`. Matching on ID (or accepting either) would
be less surprising.
