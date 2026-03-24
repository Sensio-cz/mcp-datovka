"""MCP tools for datova schranka (ISDS)."""

import json
import logging

from mcp.server.fastmcp import FastMCP

from ..config import get_boxes, get_box
from ..services import isds

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP):

    @mcp.tool()
    def datovka_list_boxes() -> str:
        """List all configured data boxes with their aliases and IDs.

        Returns a JSON array of configured boxes.
        """
        boxes = get_boxes()
        result = [{"alias": b.alias, "box_id": b.box_id} for b in boxes]
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    def datovka_list_received(
        box_alias: str,
        from_date: str | None = None,
        max_results: int = 50,
    ) -> str:
        """List received messages for a data box.

        Args:
            box_alias: Alias of the box (e.g. "sensio", "svj-jaselska")
            from_date: Optional ISO date filter (e.g. "2026-03-01")
            max_results: Max messages to return (default 50)
        """
        box = get_box(box_alias)
        if not box:
            return json.dumps({"error": f"Box '{box_alias}' not found. Use datovka_list_boxes to see available boxes."})
        messages = isds.list_received(box, from_date=from_date, max_results=max_results)
        return json.dumps(messages, ensure_ascii=False)

    @mcp.tool()
    def datovka_list_sent(
        box_alias: str,
        from_date: str | None = None,
        max_results: int = 50,
    ) -> str:
        """List sent messages for a data box.

        Args:
            box_alias: Alias of the box (e.g. "sensio", "svj-jaselska")
            from_date: Optional ISO date filter (e.g. "2026-03-01")
            max_results: Max messages to return (default 50)
        """
        box = get_box(box_alias)
        if not box:
            return json.dumps({"error": f"Box '{box_alias}' not found."})
        messages = isds.list_sent(box, from_date=from_date, max_results=max_results)
        return json.dumps(messages, ensure_ascii=False)

    @mcp.tool()
    def datovka_read_message(box_alias: str, message_id: str) -> str:
        """Read a message with its attachments (metadata + base64 content).

        Args:
            box_alias: Alias of the box
            message_id: ISDS message ID
        """
        box = get_box(box_alias)
        if not box:
            return json.dumps({"error": f"Box '{box_alias}' not found."})
        message = isds.read_message(box, message_id)
        return json.dumps(message, ensure_ascii=False)

    @mcp.tool()
    def datovka_download_attachment(
        box_alias: str,
        message_id: str,
        attachment_index: int,
    ) -> str:
        """Download a specific attachment from a message as base64.

        Args:
            box_alias: Alias of the box
            message_id: ISDS message ID
            attachment_index: Zero-based index of the attachment
        """
        box = get_box(box_alias)
        if not box:
            return json.dumps({"error": f"Box '{box_alias}' not found."})
        attachment = isds.download_attachment(box, message_id, attachment_index)
        return json.dumps(attachment, ensure_ascii=False)

    @mcp.tool()
    def datovka_send_message(
        from_box_alias: str,
        to_box_id: str,
        subject: str,
        body: str | None = None,
        files: str | None = None,
    ) -> str:
        """Send a data message. REQUIRES explicit user approval - data messages have legal weight.

        Args:
            from_box_alias: Alias of the sending box
            to_box_id: Recipient data box ID (7 chars, e.g. "abc1234")
            subject: Message subject (dmAnnotation)
            body: Optional message body text
            files: Optional JSON array of [{filename, mime_type, content_base64}]
        """
        box = get_box(from_box_alias)
        if not box:
            return json.dumps({"error": f"Box '{from_box_alias}' not found."})

        parsed_files = None
        if files:
            parsed_files = json.loads(files)

        result = isds.send_message(
            box,
            to_box_id=to_box_id,
            subject=subject,
            body=body,
            files=parsed_files,
        )
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    def datovka_search_box(query: str, box_alias: str | None = None, box_type: str | None = None) -> str:
        """Search for a data box by name, ICO, or box ID.

        Args:
            query: Search term - company name, ICO (8 digits), or box ID (7 alphanumeric)
            box_alias: Optional - which box to use for the query (uses first configured if omitted)
            box_type: Optional - box type filter: OVM (government), PO (company), PFO (self-employed), FO (person). Required for name search.
        """
        if box_alias:
            box = get_box(box_alias)
        else:
            boxes = get_boxes()
            box = boxes[0] if boxes else None

        if not box:
            return json.dumps({"error": "No box available for search."})

        results = isds.search_box(box, query, box_type=box_type)
        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    def datovka_mark_read(box_alias: str, message_id: str) -> str:
        """Mark a message as read/downloaded.

        Args:
            box_alias: Alias of the box
            message_id: ISDS message ID
        """
        box = get_box(box_alias)
        if not box:
            return json.dumps({"error": f"Box '{box_alias}' not found."})
        success = isds.mark_read(box, message_id)
        return json.dumps({"success": success, "message_id": message_id})
