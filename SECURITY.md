# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in mcp-datovka, please report it responsibly:

1. **Do NOT open a public GitHub issue**
2. Email **info@sensio.cz** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. We will acknowledge within 48 hours and provide a fix timeline

## Security design

- Credentials are loaded from environment variables only (never hardcoded)
- Communication with ISDS is always over HTTPS/TLS
- The server runs locally via stdio - no network ports exposed
- Two-step send confirmation prevents accidental message dispatch
- No message content is logged
