# Contributing to Afterparty

Thank you for your help. This file tells you how to set up the project and make a change. It also tells you what a pull request must contain.

## Set up

You must have [uv](https://docs.astral.sh/uv/), Node.js 22 and Docker.

```bash
make setup
make dev
```

Open http://localhost:8080. Local mode signs you in with an email and no password.
On the **Connect Partiful** step, select **Use demo data** to get made-up people. You do not need a Partiful account for most changes.

## Make a change

1. Open an issue first for a large change, so that we can agree on the design.
2. Make a branch from `main`.
3. Write a test for each change in behavior. The tests are in `tests/`.
4. Run the checks:

   ```bash
   make test
   make lint
   ```

5. For a change in the web app, run the UI smoke test while `make dev` runs:

   ```bash
   make smoke
   ```

## Rules for the code

- Use made-up data only in tests, screenshots and issues. Do not put real guest lists, names or Partiful tokens in the repository.
- Put SQL in `src/afterparty/app.py` or `src/afterparty/people.py`. Every query must have the ID of the user in its filter.
- Keep the Partiful parser in `src/afterparty/core/`. Every field from Partiful is optional. A missing field must give `None`, not an error.
- If you change the designation rules in `src/afterparty/core/roles.py`, change the page `web/src/pages/HowItWorks.tsx` too.
- If you change the permissions of the connector, increase `version` in `extension/manifest.json`.
- Add a database change as a new file in `src/afterparty/migrations/`. Do not edit a migration that is already in a release.

## Pull requests

A pull request must have:

- A short description of the change and the reason for it.
- Tests that pass in CI.
- A screenshot for a visible change in the web app, with made-up data.

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
