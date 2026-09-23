# Changelog

## Unreleased

### Fixed

- **Installation on a clean machine.** Three separate defects stopped it, each
  looking like a different problem: the PEP 639 `license` field clashed with a
  `License ::` classifier (setuptools refused to build), `WSDL_DIR` and
  `package-data` pointed outside the package (so an installed copy had no WSDL
  at all), and the unbounded `mcp[cli]>=1.0.0` pulled in mcp 2.x, where
  `mcp.server.fastmcp` no longer exists.
- WSDL and XSD files moved into `mcp_datovka/wsdl/` so they ship with the package.
- `build-system` now requires `setuptools>=77.0.0`; older versions cannot read
  the PEP 639 license field and fail with a misleading error.

### Changed

- README no longer offers `pip install mcp-datovka` - the package is not on PyPI.
- README says where the `.env` file is actually looked up from (the client's
  working directory, not the checkout).

### Added

- `tests/test_baleni.py` - guards each of the three defects above, including one
  test that really builds a wheel and looks inside it.

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
