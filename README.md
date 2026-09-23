# mcp-datovka

MCP server for Czech ISDS (Informacni system datovych schranek) - the official Czech government digital mailbox system.

Enables AI assistants (Claude, Cursor, etc.) to read, send, and manage data messages across multiple data boxes through the [Model Context Protocol](https://modelcontextprotocol.io/).

## Features

- **Multi-box support** - manage up to 99 data boxes from a single server
- **Full message lifecycle** - list, read, send, and download messages with attachments
- **Data box search** - find recipients by name, ICO, or box ID
- **Production + sandbox** - supports both mojedatovaschranka.cz and czebox.cz test environment
- **Stdio transport** - runs locally, no network exposure of credentials

## Tools

| Tool | Description |
|------|-------------|
| `datovka_list_boxes` | List all configured data boxes |
| `datovka_list_received` | List received messages (with date filter) |
| `datovka_list_sent` | List sent messages (with date filter) |
| `datovka_read_message` | Read message detail with attachments |
| `datovka_download_attachment` | Download a specific attachment (base64) |
| `datovka_send_message` | Send a data message with attachments |
| `datovka_search_box` | Search for a data box by name/ICO/ID |
| `datovka_mark_read` | Mark a message as read |

## Requirements

- Python 3.11+
- ISDS credentials (username + password) for each data box
  - Obtain from [mojedatovaschranka.cz](https://www.mojedatovaschranka.cz) > Nastaveni > Moznosti prihlaseni

## Installation

Install from source - the package is **not published on PyPI yet**, so
`pip install mcp-datovka` does not work:

```bash
git clone https://github.com/Sensio-cz/mcp-datovka.git
cd mcp-datovka
pip install .        # pro vyvoj: pip install -e .
```

## Configuration

### 1. Create `.env` file

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Test environment (czebox.cz) - set to "true" for sandbox
DATOVKA_TEST_ENV=false

# Box 1
DATOVKA_BOX_1_ALIAS=my-company
DATOVKA_BOX_1_ID=abc1234
DATOVKA_BOX_1_USERNAME=your_username
DATOVKA_BOX_1_PASSWORD=your_password

# Box 2
DATOVKA_BOX_2_ALIAS=personal
DATOVKA_BOX_2_ID=def5678
DATOVKA_BOX_2_USERNAME=username2
DATOVKA_BOX_2_PASSWORD=password2
```

Each box needs 4 environment variables with a sequential number (1-99):
- `DATOVKA_BOX_N_ALIAS` - friendly name used in tool calls
- `DATOVKA_BOX_N_ID` - ISDS box ID (7 alphanumeric characters)
- `DATOVKA_BOX_N_USERNAME` - ISDS login username
- `DATOVKA_BOX_N_PASSWORD` - ISDS login password

### 2. Add to your MCP client

#### Claude Code / Claude Desktop

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "datovka": {
      "command": "mcp-datovka",
      "env": {
        "DATOVKA_BOX_1_ALIAS": "my-company",
        "DATOVKA_BOX_1_ID": "abc1234",
        "DATOVKA_BOX_1_USERNAME": "your_username",
        "DATOVKA_BOX_1_PASSWORD": "your_password"
      }
    }
  }
}
```

Or using a `.env` file. **Careful:** it is looked up from the working directory
of the MCP client process, not from the checkout - after `pip install .` those
are two different places. Give the client a working directory that holds the
`.env`, or pass the credentials in `env` as above.

```json
{
  "mcpServers": {
    "datovka": {
      "command": "mcp-datovka"
    }
  }
}
```

#### Cursor

Add to `.cursor/mcp.json` with the same format.

## Usage examples

### List received messages

```
"Show me received messages in my-company data box"
```

The AI assistant calls `datovka_list_received(box_alias="my-company")` and displays the results.

### Send a document

```
"Send invoice.pdf to data box abc1234 from my-company box with subject 'Invoice 2026/03'"
```

The assistant calls `datovka_send_message` with the file content as base64.

### Search for a recipient

```
"Find the data box for ICO 04004621"
```

The assistant calls `datovka_search_box(query="04004621")`.

### Cross-channel workflow (with Gmail MCP)

```
"Take the attachment from the email by Novak and send it via data box to the tax office"
```

The assistant:
1. Downloads the attachment from Gmail (`gmail_get_attachment_content`)
2. Sends it via ISDS (`datovka_send_message`)

## ISDS API details

This server communicates with ISDS via SOAP/HTTPS using bundled WSDL definitions from [dslib](https://github.com/yarda/dslib) (CZ.NIC).

| Operation | WSDL | SOAP endpoint |
|-----------|------|---------------|
| List messages | `dm_info.wsdl` | `/DS/dx` |
| Send/download messages | `dm_operations.wsdl` | `/DS/dz` |
| Search data boxes | `db_search.wsdl` | `/DS/df` |

**Authentication:** HTTP Basic Auth over HTTPS. Each box authenticates independently.

**Environments:**

| Environment | Base URL |
|-------------|----------|
| Production | `https://ws1.mojedatovaschranka.cz` |
| Test (sandbox) | `https://ws1.czebox.cz` |

## Testing with sandbox

1. Log in to [mojedatovaschranka.cz](https://www.mojedatovaschranka.cz)
2. Go to Nastaveni > Pro vyvojare
3. Create test data boxes (up to 4)
4. Set `DATOVKA_TEST_ENV=true` in `.env`
5. Use sandbox credentials

## Security

### Two-step send confirmation (HITL)

The `datovka_send_message` tool implements a **mandatory two-step confirmation flow**:

1. **First call** (`confirmed=false`, default) - returns a preview of the message (sender, recipient, subject, attachments) without sending anything
2. **Second call** (`confirmed=true`) - actually sends the message, but only after the AI has shown the preview to the user and received explicit approval

This ensures that no data message is ever sent without human approval, regardless of the AI assistant's behavior.

### Other security measures

- Credentials are stored in `.env` (gitignored) or passed via environment variables
- Communication with ISDS is always over HTTPS/TLS
- The server runs locally via stdio - no network ports are opened
- No message content is logged - only metadata (subject, sender, timestamp)
- Each box authenticates independently - compromising one box does not affect others

## Legal notice

Data messages (datove zpravy) sent through ISDS have the **legal effect of delivery by registered mail** under Czech law (Act No. 300/2008 Coll.). Use this tool responsibly and always verify the recipient before sending.

## License

MIT

## Credits

- WSDL definitions from [dslib](https://github.com/yarda/dslib) by CZ.NIC (LGPL)
- Built with [zeep](https://github.com/mvantellingen/python-zeep) SOAP client
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
