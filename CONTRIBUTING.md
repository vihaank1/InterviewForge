# Contributing

Thanks for considering a contribution. Please file an issue describing a clear reproduction or narrowly scoped proposal before a major change.

To work locally, follow the README setup, then run `python -m pytest -q` from `backend/` and `npm run build` from `frontend/`. New backend endpoints should include a test using an injected fake provider—do not make CI depend on billable OpenAI calls. Keep `.env` files and API keys out of commits.

For a pull request, describe the behavior change, tests performed, and any limitations. AI feedback is not a hiring benchmark; don't add accuracy claims without evidence.
