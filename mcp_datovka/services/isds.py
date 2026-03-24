"""ISDS SOAP client using zeep with local WSDL files."""

import base64
import logging
from pathlib import Path
from datetime import datetime

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.helpers import serialize_object

from ..config import BoxConfig, get_soap_urls

logger = logging.getLogger(__name__)

WSDL_DIR = Path(__file__).parent.parent.parent / "wsdl"


class _RemoveNilPlugin:
    """Zeep plugin that removes xsi:nil elements from outgoing requests."""

    def ingress(self, envelope, http_headers, operation):
        return envelope, http_headers

    def egress(self, envelope, http_headers, operation, binding_options):
        # Remove all elements with xsi:nil="true"
        XSI = "http://www.w3.org/2001/XMLSchema-instance"
        for elem in envelope.iter():
            if elem.get(f"{{{XSI}}}nil") == "true":
                elem.getparent().remove(elem)
        return envelope, http_headers


def _create_client(wsdl_name: str, box: BoxConfig) -> Client:
    """Create a zeep SOAP client with Basic Auth for a given WSDL."""
    wsdl_path = WSDL_DIR / wsdl_name
    if not wsdl_path.exists():
        raise FileNotFoundError(f"WSDL not found: {wsdl_path}")

    session = Session()
    session.auth = HTTPBasicAuth(box.username, box.password)
    session.verify = True
    transport = Transport(session=session)
    settings = Settings(strict=False, xml_huge_tree=True)

    return Client(str(wsdl_path), transport=transport, settings=settings, plugins=[_RemoveNilPlugin()])


def _get_operations_client(box: BoxConfig) -> Client:
    client = _create_client("dm_operations.wsdl", box)
    client.service._binding_options["address"] = get_soap_urls()["operations"]
    return client


def _get_info_client(box: BoxConfig) -> Client:
    client = _create_client("dm_info.wsdl", box)
    client.service._binding_options["address"] = get_soap_urls()["info"]
    return client


def _get_search_client(box: BoxConfig) -> Client:
    client = _create_client("db_search.wsdl", box)
    client.service._binding_options["address"] = get_soap_urls()["search"]
    return client


def _safe(val) -> str:
    return str(val) if val is not None else ""


def _serialize_message_dict(msg: dict) -> dict:
    """Convert a deserialized SOAP message dict to a clean dict."""
    return {
        "id": _safe(msg.get("dmID")),
        "sender_id": _safe(msg.get("dbIDSender")),
        "sender": _safe(msg.get("dmSender")),
        "sender_address": _safe(msg.get("dmSenderAddress")),
        "recipient": _safe(msg.get("dmRecipient")),
        "recipient_id": _safe(msg.get("dbIDRecipient")),
        "subject": _safe(msg.get("dmAnnotation")),
        "delivery_time": _format_datetime(msg.get("dmDeliveryTime")),
        "acceptance_time": _format_datetime(msg.get("dmAcceptanceTime")),
        "status": _safe(msg.get("dmMessageStatus")),
        "attachment_size": _safe(msg.get("dmAttachmentSize")),
    }


def _format_datetime(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def list_received(box: BoxConfig, from_date: str | None = None, max_results: int = 50) -> list[dict]:
    """List received messages for a box."""
    client = _get_info_client(box)
    try:
        # GetListOfReceivedMessages params: dmFromTime, dmToTime, dmRecipientOrgUnitNum,
        # dmStatusFilter (1=all, 2=unread), dmOffset, dmLimit
        kwargs = {
            "dmStatusFilter": 1,
            "dmLimit": max_results,
            "dmOffset": 1,
        }
        if from_date:
            kwargs["dmFromTime"] = datetime.fromisoformat(from_date)

        response = client.service.GetListOfReceivedMessages(**kwargs)
        resp_dict = serialize_object(response, dict)

        status = resp_dict.get("dmStatus", {})
        status_code = str(status.get("dmStatusCode", ""))
        if status_code != "0000":
            status_msg = str(status.get("dmStatusMessage", ""))
            logger.error(f"ISDS error: {status_code} - {status_msg}")
            return []

        # Response uses dmRecords._value_1 or dmRecord
        records_container = resp_dict.get("dmRecords") or resp_dict.get("dmRecord")
        if not records_container:
            return []

        # May be dict with _value_1, list, or single dict
        if isinstance(records_container, dict):
            records = records_container.get("_value_1", [records_container])
        elif isinstance(records_container, list):
            records = records_container
        else:
            return []

        if not records:
            return []

        # Each record may be wrapped in dmRecord key
        result = []
        for r in records:
            if isinstance(r, dict) and "dmRecord" in r:
                result.append(_serialize_message_dict(r["dmRecord"]))
            elif isinstance(r, dict):
                result.append(_serialize_message_dict(r))
        return result
    except Exception as e:
        logger.error(f"list_received failed for {box.alias}: {e}")
        raise


def list_sent(box: BoxConfig, from_date: str | None = None, max_results: int = 50) -> list[dict]:
    """List sent messages for a box."""
    client = _get_info_client(box)
    try:
        kwargs = {
            "dmStatusFilter": 1,
            "dmLimit": max_results,
            "dmOffset": 1,
        }
        if from_date:
            kwargs["dmFromTime"] = datetime.fromisoformat(from_date)

        response = client.service.GetListOfSentMessages(**kwargs)
        resp_dict = serialize_object(response, dict)

        status = resp_dict.get("dmStatus", {})
        status_code = str(status.get("dmStatusCode", ""))
        if status_code != "0000":
            status_msg = str(status.get("dmStatusMessage", ""))
            logger.error(f"ISDS error: {status_code} - {status_msg}")
            return []

        records = resp_dict.get("dmRecord", [])
        if not records:
            return []
        if isinstance(records, dict):
            records = [records]

        return [_serialize_message_dict(msg) for msg in records]
    except Exception as e:
        logger.error(f"list_sent failed for {box.alias}: {e}")
        raise


def read_message(box: BoxConfig, message_id: str) -> dict:
    """Download a message with attachments."""
    client = _get_operations_client(box)
    try:
        response = client.service.MessageDownload(dmID=message_id)
        resp_dict = serialize_object(response, dict)

        status = resp_dict.get("dmStatus", {})
        status_code = str(status.get("dmStatusCode", ""))
        if status_code != "0000":
            status_msg = str(status.get("dmStatusMessage", ""))
            raise RuntimeError(f"ISDS error: {status_code} - {status_msg}")

        dm_return = resp_dict.get("dmReturnedMessage", {})
        envelope = dm_return.get("dmDm", {})
        files_container = dm_return.get("dmFiles", {})

        result = _serialize_message_dict(envelope) if envelope else {"id": message_id}

        attachments = []
        if files_container:
            file_list = files_container.get("dmFile", [])
            if file_list is None:
                file_list = []
            if isinstance(file_list, dict):
                file_list = [file_list]
            for f in file_list:
                content = f.get("dmEncodedContent")
                # content may be bytes from zeep
                if isinstance(content, bytes):
                    content_b64 = base64.b64encode(content).decode("ascii")
                    size = len(content)
                elif content:
                    content_b64 = str(content)
                    size = len(base64.b64decode(content))
                else:
                    content_b64 = None
                    size = 0
                attachments.append({
                    "filename": _safe(f.get("_dmFileDescr")),
                    "mime_type": _safe(f.get("_dmMimeType")) or "application/octet-stream",
                    "size_bytes": size,
                    "content_base64": content_b64,
                })

        result["attachments"] = attachments
        return result
    except Exception as e:
        logger.error(f"read_message failed for {box.alias}/{message_id}: {e}")
        raise


def download_attachment(box: BoxConfig, message_id: str, attachment_index: int) -> dict:
    """Download a specific attachment from a message."""
    msg = read_message(box, message_id)
    attachments = msg.get("attachments", [])
    if attachment_index < 0 or attachment_index >= len(attachments):
        raise ValueError(f"Attachment index {attachment_index} out of range (0-{len(attachments)-1})")
    return attachments[attachment_index]


def send_message(
    box: BoxConfig,
    to_box_id: str,
    subject: str,
    body: str | None = None,
    files: list[dict] | None = None,
) -> dict:
    """Send a data message.

    files: list of {filename, mime_type, content_base64}
    """
    client = _get_operations_client(box)
    try:
        # Build envelope
        envelope_type = client.get_type("ns2:dmEnvelope")
        envelope = envelope_type(
            dbIDRecipient=to_box_id,
            dmAnnotation=subject,
        )

        # Build files
        dm_files = []
        if files:
            file_type = client.get_type("ns2:dmFile")
            for i, f in enumerate(files):
                dm_file = file_type(
                    _dmFileDescr=f["filename"],
                    _dmMimeType=f.get("mime_type", "application/octet-stream"),
                    _dmFileMetaType="main" if i == 0 else "enclosure",
                    dmEncodedContent=f["content_base64"],
                )
                dm_files.append(dm_file)

        # If body text provided, add as text attachment
        if body and not files:
            file_type = client.get_type("ns2:dmFile")
            dm_file = file_type(
                _dmFileDescr="zprava.txt",
                _dmMimeType="text/plain",
                _dmFileMetaType="main",
                dmEncodedContent=base64.b64encode(body.encode("utf-8")).decode("ascii"),
            )
            dm_files.append(dm_file)

        files_container_type = client.get_type("ns2:dmFiles")
        files_container = files_container_type(dmFile=dm_files)

        response = client.service.CreateMessage(
            dmEnvelope=envelope,
            dmFiles=files_container,
        )

        status_code = str(getattr(response.dmStatus, "dmStatusCode", ""))
        status_msg = str(getattr(response.dmStatus, "dmStatusMessage", ""))

        if status_code != "0000":
            raise RuntimeError(f"ISDS error: {status_code} - {status_msg}")

        return {
            "message_id": str(getattr(response, "dmID", "")),
            "status": "sent",
            "status_message": status_msg,
        }
    except Exception as e:
        logger.error(f"send_message failed for {box.alias} -> {to_box_id}: {e}")
        raise


def search_box(box: BoxConfig, query: str) -> list[dict]:
    """Search for a data box by name, ICO, or ID."""
    client = _get_search_client(box)
    try:
        owner_info_type = client.get_type("{http://isds.czechpoint.cz/v20}tDbOwnerInfo")

        # Try to detect query type and build search params
        kwargs = {}
        if query.isdigit() and len(query) == 8:
            kwargs["ic"] = query
        elif len(query) == 7 and query.isalnum():
            kwargs["dbID"] = query
        else:
            kwargs["firmName"] = query

        search = owner_info_type(**kwargs)

        response = client.service.FindDataBox(dbOwnerInfo=search)

        # Response can be a dict-like or object - handle both
        resp_dict = serialize_object(response, dict)

        status = resp_dict.get("dbStatus", {})
        status_code = str(status.get("dbStatusCode", ""))
        if status_code != "0000":
            status_msg = str(status.get("dbStatusMessage", ""))
            logger.warning(f"Search returned: {status_code} - {status_msg}")
            return []

        results = resp_dict.get("dbResults", {})
        if not results:
            return []

        # Results are under _value_1[].dbOwnerInfo
        value_list = results.get("_value_1", [])
        if not value_list:
            # Fallback: try direct dbOwnerInfo
            owner_list = results.get("dbOwnerInfo", [])
            if isinstance(owner_list, dict):
                owner_list = [owner_list]
        else:
            owner_list = [item.get("dbOwnerInfo", item) for item in value_list if item]

        if not owner_list:
            return []

        def _safe(val):
            return str(val) if val is not None else ""

        return [
            {
                "box_id": _safe(o.get("dbID")),
                "type": _safe(o.get("dbType")),
                "ico": _safe(o.get("ic")),
                "firm_name": _safe(o.get("firmName")),
                "first_name": _safe(o.get("pnFirstName")),
                "last_name": _safe(o.get("pnLastName")),
                "city": _safe(o.get("adCity")),
                "street": _safe(o.get("adStreet")),
                "zip": _safe(o.get("adZipCode")),
                "state": _safe(o.get("dbState")),
            }
            for o in owner_list
        ]
    except Exception as e:
        logger.error(f"search_box failed: {e}")
        raise


def mark_read(box: BoxConfig, message_id: str) -> bool:
    """Mark a message as downloaded/read."""
    client = _get_info_client(box)
    try:
        response = client.service.MarkMessageAsDownloaded(dmID=message_id)
        resp_dict = serialize_object(response, dict)
        status = resp_dict.get("dmStatus", {})
        status_code = str(status.get("dmStatusCode", ""))
        return status_code == "0000"
    except Exception as e:
        logger.error(f"mark_read failed for {box.alias}/{message_id}: {e}")
        raise
