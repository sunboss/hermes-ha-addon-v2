# Release checklist

## Before tagging
- [ ] `pytest -q`
- [ ] CI workflow is green on `main`
- [ ] `hermes_agent_v2/config.yaml` version matches intended release
- [ ] `README.md` version updated
- [ ] `CHANGELOG.md` updated
- [ ] `INSTALL.md` still matches current behavior
- [ ] No secrets committed

## Tagging
- [ ] `git tag -a vX.Y.Z -m "release vX.Y.Z"`
- [ ] `git push origin main --tags`

## After tagging
- [ ] Confirm GitHub Actions `release.yml` ran
- [ ] Confirm GitHub Release was created
- [ ] Confirm release notes are sane
- [ ] Optional: install from a clean HA instance and smoke test UI, auth, panel, workspace
