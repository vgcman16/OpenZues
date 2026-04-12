# Security Policy

OpenZues is a local-first control plane that can bridge into powerful tools, local filesystems, GitHub access,
and autonomous operator workflows. Please treat security issues seriously.

## Supported builds

Security fixes are only guaranteed for the latest code on `main` and the most recent public alpha state.

## What to report

Please report issues such as:

- auth or approval bypasses
- unintended remote command execution
- secret or token disclosure
- unsafe filesystem access outside the expected workspace scope
- sandbox or permission-boundary escapes
- SSRF, webhook abuse, or unsafe remote connection handling

## Preferred reporting path

Please do not post high-risk vulnerability details in a public issue.

Preferred path:

1. Use GitHub Private Vulnerability Reporting or a repository security advisory if it is enabled.
2. If no private reporting path is available, open a minimal public issue requesting a secure contact path and
   do not include exploit details, tokens, screenshots of secrets, or reproduction payloads.

## What helps a report

- affected version or commit
- deployment model and operating system
- clear reproduction steps
- impact assessment
- whether the issue requires prior local access or can be triggered remotely

## Operator safety guidance

- Keep approval pauses enabled for risky actions unless you have a strong reason not to.
- Avoid exposing local-first services directly to the public internet without an explicit auth and threat review.
- Never include real secrets in issues, logs, screenshots, or sample configs.
