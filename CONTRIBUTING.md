# Contributing to FreeStream

Thanks for your interest in contributing to FreeStream! This document explains how to report issues, propose changes, and get code merged. Follow the guidance below to make the review process fast and simple.

---

## Quick links
- User-facing docs and setup: `README.md`
- Configuration template: `SETTINGS.example.py`

---

## Code of Conduct
Be respectful and professional. I will leave it there unless more proves to be needed.

---

## How to report an issue
When opening an issue, include:
- Clear title and short summary
- Steps to reproduce
- Expected behavior vs actual behavior
- Version and environment (Docker / OS / Docker Compose version)
- Relevant logs (use `docker compose logs freestream` and `docker compose logs piper`)
- `SETTINGS.py` snippet (non-sensitive only) or mention which settings you used

Label issues according to domain (e.g., `bug`, `enhancement`, `docs`, `security`).

---

## Feature requests & design discussions
- If the change is architectural or affects integrations (Twitch/YouTube/Piper), open an issue first to discuss scope and design.
- Reference `AGENTS.md` for architectural constraints and design expectations.
- Use issues to gather feedback and iterate on the design before writing code.

---

## Development setup (recommended)
Prefer Docker for parity with production, or run locally with a virtualenv.

Docker (recommended):
```bash
git clone <repo-url>
cp SETTINGS.example.py SETTINGS.py
# Edit SETTINGS.py with your credentials and preferences (do NOT commit)
docker compose up -d
```

Local (non-Docker):
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp SETTINGS.example.py SETTINGS.py
python -m app.main
```

For Twitch EventSub webhooks during local dev, use `ngrok http 5000` and set `TWITCH_WEBHOOK_CALLBACK_URL` accordingly.

---

## Branching & commit guidelines
- Create topic branches from `main` using descriptive names:
  - `feature/<short-description>` for new features
  - `fix/<short-description>` for bug fixes
  - `docs/<short-description>` for documentation changes
- Use Conventional Commits style for messages:
  - `feat(twitch): add event handler for channel.cheer`
  - `fix(tts): avoid crash on empty message`
- Keep commits small and focused.

---

## Pull Request checklist
Before requesting review, ensure:
- [ ] Changes include tests (unit / integration / end-to-end as needed)
- [ ] All tests pass locally (`pytest`)
- [ ] Linting and formatting applied (`ruff`, `black`, `isort`)
- [ ] Documentation updated (README, AGENTS.md, or SETTINGS.example.py if relevant)
- [ ] PR description explains the motivation and implementation details
- [ ] If the change is breaking, include migration notes and update `AGENTS.md` accordingly

A good PR description should include: problem statement, design summary, testing strategy, and any follow-up work.

---

## Testing strategy
- Unit tests for core logic (event processing, message templating, profanity filtering)
- Integration tests for TTS generation (mock Piper / Wyoming or use a test piper container)
- End-to-end tests for the full flow (fake events injection mode described in `AGENTS.md`)

Run tests:
```bash
docker compose exec freestream pytest
# or locally
pytest
```
Aim for high coverage on event processing and TTS queuing.

---

## Linting & formatting
Suggested tools:
- `black` for formatting
- `ruff` for linting
- `isort` for import ordering
- `pre-commit` hooks to run checks locally before committing

Install and run pre-commit:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

---

## Security and sensitive data
- **Never** commit `SETTINGS.py` with real credentials or any token files. Use `SETTINGS.example.py` as a template.
- Follow the guidelines in `.gitignore` for ignoring `tokens/`, `data/`, and audio cache.
- For security vulnerabilities, open a private issue or email the maintainers (TODO: add contact details in the repo) — do not disclose secrets publicly.

---

## CI / CD recommendations
- Use GitHub Actions (or equivalent) to run linting, tests, and build steps on each PR
- Run integration tests against a lightweight piper test container (or a mocked HTTP/Wyoming endpoint)
- Require passing CI and at least one review before merging

---

## Release & versioning
- Use Semantic Versioning (semver.org)
- Keep a `CHANGELOG.md` with short, structured entries per release

---

## Gotchas & project-specific notes
- Piper integration: implement either Wyoming protocol, a local HTTP piper API, or CLI mode. Document approach in `AGENTS.md`.
- Twitch EventSub: local development needs a public HTTPS callback. Consider adding a `dev` mode for WebSocket EventSub.
- YouTube LiveChat: be mindful of API quotas and polling intervals — provide config knobs in `SETTINGS.py`.

---

## Acknowledgements
Thanks for contributing—your help makes FreeStream better and more reliable for streamers!

If you have questions, open an issue or start a discussion in the repo.
