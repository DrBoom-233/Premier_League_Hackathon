# Team workflow

## Collaboration

- Treat `main` as the stable, shareable version.
- Create a short branch for each task: `feat/<topic>`, `fix/<topic>`, or `docs/<topic>`.
- Open a pull request for changes and ask one teammate to review it before merging when time allows.
- Keep pull requests focused and describe what changed, how to run or inspect it, and any follow-up work.
- Use GitHub Issues for tasks and decisions that need group input. Put durable technical and product decisions in `docs/DECISIONS.md`.

## Project notes

- Keep `docs/PROJECT_BRIEF.md` current as the concept changes.
- Use synthetic football-realistic event data unless the team confirms the license and permitted use of another source.
- Do not commit credentials, API keys, personal data, or unlicensed match footage/data. Put local secrets in `.env` and keep `.env` untracked; document required variable names in `.env.example` without values.
- Keep all submission-facing content in English, as required by the hackathon rules.

## Commit messages

Use concise messages such as `feat: add event timeline` or `docs: clarify demo flow`.
