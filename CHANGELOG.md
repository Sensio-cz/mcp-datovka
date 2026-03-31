# Changelog

## 0.2.0 (2026-03-31)

### Fixes

- `files` parameter in `datovka_send_message` now accepts both `str` and `list` (MCP SDK auto-parses JSON strings)
- URL-safe base64 from Gmail API (`-_` instead of `+/`) is automatically converted to standard base64

### Added

- Comprehensive README with prerequisites, installation, configuration, usage examples, troubleshooting
- CONTRIBUTING.md with development setup guide
- SECURITY.md with vulnerability reporting policy
- `__version__` constant in package
- Automated test suite (config, tools, ISDS client, base64 handling)
- Dev dependencies (pytest, pytest-cov)

## 0.1.0 (2026-03-24)

Initial release.

### Features

- 8 MCP tools: `datovka_list_boxes`, `datovka_list_received`, `datovka_list_sent`, `datovka_read_message`, `datovka_download_attachment`, `datovka_send_message`, `datovka_search_box`, `datovka_mark_read`
- Multi-box support (up to 99 data boxes via environment variables)
- ISDS SOAP client using zeep with bundled WSDL files
- Production (mojedatovaschranka.cz) and sandbox (czebox.cz) support
- HTTP Basic Auth with username/password per box
- Send messages with file attachments (PDF, XML, and all ISDS-supported formats)
- Search data boxes by ICO, box ID, or company/person name
- Stdio transport (local execution, no network exposure)
