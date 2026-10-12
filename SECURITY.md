# Security policy

Afterparty keeps Partiful sign-in tokens and the guest lists of its users. Please report security problems in private.

## Report a problem

Use GitHub's private vulnerability reporting: open the **Security** tab of this repository and select **Report a vulnerability**.
Do not open a public issue for a security problem.

Include the steps to reproduce the problem and the version or commit that you used.
We will reply in 7 days.

## In scope

- Access to the data of a different user.
- Ways to read or decrypt a stored Partiful token.
- Ways to make the connector give a Partiful sign-in to a page that is not the instance.
- Sign-in bypass in Firebase mode, or a bypass of `ALLOWED_EMAILS`.

## Out of scope

- Local mode (`APP_ENV=dev`). It has no password by design and is only for a computer that nobody else can reach.
- Changes in Partiful's API or terms.
