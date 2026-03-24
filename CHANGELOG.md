# Changelog

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
