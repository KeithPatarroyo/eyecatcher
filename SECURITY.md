# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

Other versions are not actively supported. We recommend upgrading to the latest release.

## Reporting a Vulnerability

**Please do not report security vulnerabilities in public GitHub issues.**

If you believe you have found a security issue:

1. **Contact the maintainers privately** — Open a GitHub issue with a private report, or contact the repository owners through the contact method listed in the repository (e.g. in the Code of Conduct or README).
2. **Describe the issue** — Include steps to reproduce, affected components, and potential impact.
3. **Give us time** — We will acknowledge your report and aim to respond within a reasonable timeframe. We may ask for more details or work with you on a fix before any public disclosure.

We appreciate responsible disclosure and will credit reporters (with their permission) when we announce fixes.

## Security Considerations for Deployments

- Set a strong `ADMIN_KEY` in production; do not use the default `ALICE` from development.
- Restrict `CORS_ORIGINS` to your actual front-end origin(s).
- Keep dependencies up to date (`pip install -e ".[dev]"` and periodic updates).
- Run the application with least-privilege user accounts where possible.
