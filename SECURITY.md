# Security notes

## Trust boundaries

- CI3-to-FastAPI uses an API key only in a server-side header. Never expose it in browser JavaScript.
- The CI3 client selector is for local demo simulation only. Production client identity must come from portal authentication.
- Report chunks are untrusted text. Prompt-like instructions in documents are never executable policy.
- Entitlement lookup happens before vector retrieval. A second allow-list assertion runs before context construction.

## Data access

Entitlements use a composite-key join table. Unauthorized report content is not fetched into evidence. Responses may disclose that an inaccessible report exists, but not its figures. The aggregate tool uses a fixed SELECT statement with a bounded result count; the model cannot submit SQL. A dedicated read-only MySQL account is provisioned for that database boundary. Application writes use the normal app DB role.

## Input/output protections

Pydantic limits IDs and request fields; request length is capped. Destructive SQL language and client-data exfiltration requests are blocked and logged in sanitized form. CI3 validates inputs, escapes output with `html_escape`, and enables CSRF. API errors avoid returning stack traces.

## Secrets and local configuration

Copy `.env.example` to `.env` and replace the API key and development database credentials. `.env` is gitignored. Never use the included development passwords outside a disposable local environment. Set TLS and rotate secrets in deployment.

## Current limitations

No production identity provider, rate limiter, distributed tracing, or semantic cache is included. The CI3 selector is not authentication. Prompt-injection detection uses pattern indicators plus a strict system boundary; pattern checks alone are not a complete detector. The critic's numeric check is not semantic entailment. These are known remaining hardening tasks.
