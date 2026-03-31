# mcp-datovka

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

MCP server for Czech ISDS (Informacni system datovych schranek) - the official Czech government digital mailbox system.

Enables AI assistants (Claude, Cursor, etc.) to read, send, and manage data messages across multiple data boxes through the [Model Context Protocol](https://modelcontextprotocol.io/).

> **Co je datova schranka?** Datova schranka (data box) is a mandatory electronic communication channel between Czech citizens/companies and government authorities. Messages sent via ISDS have the **legal effect of registered mail** (Act No. 300/2008 Coll.).

## Features

- **Multi-box support** - manage up to 99 data boxes from a single server
- **Full message lifecycle** - list, read, send, and download messages with attachments
- **Data box search** - find recipients by name, ICO, or box ID
- **Two-step send confirmation** - mandatory human-in-the-loop before sending (legal safety)
- **Cross-channel workflows** - works with Gmail MCP, Google Drive MCP, and others
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
| `datovka_send_message` | Send a data message with attachments (two-step confirmation) |
| `datovka_search_box` | Search for a data box by name/ICO/ID |
| `datovka_mark_read` | Mark a message as read |

## Prerequisites

Before installation, you need:

1. **Python 3.11 or higher** - [download](https://www.python.org/downloads/)
2. **ISDS credentials** (username + password) for each data box you want to manage
   - Log in to [mojedatovaschranka.cz](https://www.mojedatovaschranka.cz)
   - Go to *Nastaveni > Moznosti prihlaseni*
   - Create or note your login credentials (username + password authentication)
3. **Data box ID** (7-character alphanumeric string, e.g. `abc1234`)
   - Visible in your data box settings or on any received message

> **Sandbox testing:** You can test without real credentials using the ISDS sandbox (czebox.cz). See [Testing with sandbox](#testing-with-sandbox).

## Installation

### From PyPI (recommended)

```bash
pip install mcp-datovka
```

### From source

```bash
git clone https://github.com/Sensio-cz/mcp-datovka.git
cd mcp-datovka
pip install -e .
```

### Verify installation

```bash
mcp-datovka --help
```

## Configuration

### Step 1: Create `.env` file

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Test environment (czebox.cz) - set to "true" for sandbox
DATOVKA_TEST_ENV=false

# Box 1
DATOVKA_BOX_1_ALIAS=my-company
DATOVKA_BOX_1_ID=abc1234
DATOVKA_BOX_1_USERNAME=your_username
DATOVKA_BOX_1_PASSWORD=your_password

# Box 2 (optional)
DATOVKA_BOX_2_ALIAS=personal
DATOVKA_BOX_2_ID=def5678
DATOVKA_BOX_2_USERNAME=username2
DATOVKA_BOX_2_PASSWORD=password2
```

Each box needs 4 environment variables with a sequential number (1-99):

| Variable | Description | Example |
|----------|-------------|---------|
| `DATOVKA_BOX_N_ALIAS` | Friendly name used in tool calls | `my-company` |
| `DATOVKA_BOX_N_ID` | ISDS box ID (7 alphanumeric chars) | `abc1234` |
| `DATOVKA_BOX_N_USERNAME` | ISDS login username | `john_doe` |
| `DATOVKA_BOX_N_PASSWORD` | ISDS login password | `secret123` |

> **Important:** Never commit `.env` to git. The `.gitignore` already excludes it.

### Step 2: Add to your MCP client

#### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "datovka": {
      "command": "mcp-datovka"
    }
  }
}
```

The server will automatically load credentials from `.env` in the current directory.

Alternatively, pass credentials directly via env:

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

#### Claude Desktop

Add to your Claude Desktop config (`claude_desktop_config.json`):

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

#### Cursor

Add to `.cursor/mcp.json` with the same format as Claude Code.

## Usage

### List your data boxes

```
"What data boxes do I have configured?"
```

### List received messages

```
"Show me messages received in my-company data box since March 1st"
```

### Read a message

```
"Read message 1234567 from my-company box"
```

### Send a document

```
"Send invoice.pdf to data box abc1234 from my-company box with subject 'Invoice 2026/03'"
```

The assistant will:
1. Prepare the message and show you a **preview** (recipient, subject, attachments)
2. Wait for your explicit **approval** before sending
3. Send the message only after you confirm

### Search for a recipient

```
"Find the data box for ICO 04004621"
```

```
"Search for Financni urad Prerov"
```

### Download an attachment

```
"Download the first attachment from message 1234567 in my-company box"
```

### Cross-channel workflow (Gmail + Datovka)

```
"Take the XML attachment from the email by Buresova and send it via data box to the tax office"
```

The assistant will:
1. Download the attachment from Gmail (using gmail MCP)
2. Search for the tax office data box
3. Show you a preview and wait for approval
4. Send it via ISDS

## How it works

```
AI Assistant <--stdio--> mcp-datovka <--SOAP/HTTPS--> ISDS (mojedatovaschranka.cz)
```

1. The MCP client (Claude, Cursor) starts `mcp-datovka` as a local subprocess
2. Communication happens over stdio (standard input/output) - no network ports opened
3. `mcp-datovka` translates MCP tool calls into ISDS SOAP API calls
4. All communication with ISDS is over HTTPS/TLS with HTTP Basic Auth
5. Credentials never leave your machine

### ISDS API details

| Operation | WSDL | SOAP endpoint |
|-----------|------|---------------|
| List messages | `dm_info.wsdl` | `/DS/dx` |
| Send/download | `dm_operations.wsdl` | `/DS/dz` |
| Search boxes | `db_search.wsdl` | `/DS/df` |

**Environments:**

| Environment | Base URL | Purpose |
|-------------|----------|---------|
| Production | `https://ws1.mojedatovaschranka.cz` | Real messages with legal effect |
| Sandbox | `https://ws1.czebox.cz` | Testing without legal consequences |

## Testing with sandbox

1. Log in to [mojedatovaschranka.cz](https://www.mojedatovaschranka.cz)
2. Go to *Nastaveni > Pro vyvojare*
3. Create test data boxes (up to 4)
4. Set `DATOVKA_TEST_ENV=true` in `.env`
5. Use sandbox credentials

Messages sent in sandbox have **no legal effect** and are automatically deleted.

## Security

### Two-step send confirmation (Human-in-the-Loop)

The `datovka_send_message` tool implements a **mandatory two-step confirmation flow**:

1. **Preview** (`confirmed=false`, default) - returns message details without sending
2. **Send** (`confirmed=true`) - actually sends, but only after the AI has shown the preview to the user and received explicit approval

This ensures that no data message is ever sent without human approval, regardless of the AI assistant's behavior. This is critical because data messages have the legal effect of registered mail.

### Credential security

- Credentials are stored in `.env` (gitignored) or passed via environment variables
- Credentials are never logged, printed, or exposed in tool responses
- Each box authenticates independently - compromising one doesn't affect others

### Network security

- Communication with ISDS is always over HTTPS/TLS
- The server runs locally via stdio - no network ports are opened
- No message content is logged - only metadata for debugging

### Base64 compatibility

The server automatically handles URL-safe base64 encoding (used by Gmail API) by converting it to standard base64 before sending to ISDS. This enables seamless cross-channel workflows without manual encoding steps.

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `No boxes configured` | Missing env vars | Check `.env` file exists and has `DATOVKA_BOX_1_*` vars |
| `Box 'X' not found` | Typo in alias | Run `datovka_list_boxes` to see configured aliases |
| `ISDS error: 1214` | File content doesn't match extension | Ensure base64 content matches the filename extension |
| `ISDS error: 2011` | Invalid recipient | Verify the target box ID (7 alphanumeric chars) |
| `Authentication failed` | Wrong credentials | Verify username/password at mojedatovaschranka.cz |
| `Connection refused` | Wrong environment | Check `DATOVKA_TEST_ENV` matches your credentials |

## Legal notice

Data messages (datove zpravy) sent through ISDS have the **legal effect of delivery by registered mail** under Czech law (Act No. 300/2008 Coll.). Use this tool responsibly and always verify the recipient before sending.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT - see [LICENSE](LICENSE) for details.

## Credits

- WSDL definitions from [dslib](https://github.com/yarda/dslib) by CZ.NIC (LGPL)
- Built with [zeep](https://github.com/mvantellingen/python-zeep) SOAP client
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
