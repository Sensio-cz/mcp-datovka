"""ISDS SOAP client using zeep with local WSDL files."""

import base64
import logging
from pathlib import Path
from datetime import datetime

from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport

from ..config import BoxConfig, get_soap_urls

logger = logging.getLogger(__name__)

WSDL_DIR = Path(__file__).parent.parent.parent / "wsdl"


def _create_client(wsdl_name: str, box: BoxConfig) -> Client:
    """Create a zeep SOAP client with Basic Auth for a given WSDL."""
    wsdl_path = WSDL_DIR / wsdl_name
    if not wsdl_path.exists():
        raise FileNotFoundError(f"WSDL not found: {wsdl_path}")

    session = Session()
    session.auth = HTTPBasicAuth(box.username, box.password)
    session.verify = True
    transport = Transport(session=session)

    return Client(str(wsdl_path), transport=transport)


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


def _serialize_message(msg) -> dict:
    """Convert a SOAP message object to a serializable dict."""
    return {
        "id": str(getattr(msg, "dmID", "")),
        "sender_id": str(getattr(msg, "dbIDSender", "")),
        "sender": str(getattr(msg, "dmSender", "")),
        "sender_address": str(getattr(msg, "dmSenderAddress", "")),
        "recipient": str(getattr(msg, "dmRecipient", "")),
        "recipient_id": str(getattr(msg, "dbIDRecipient", "")),
        "subject": str(getattr(msg, "dmAnnotation", "")),
        "delivery_time": _format_datetime(getattr(msg, "dmDeliveryTime", None)),
        "acceptance_time": _format_datetime(getattr(msg, "dmAcceptanceTime", None)),
        "status": str(getattr(msg, "dmMessageStatus", "")),
        "attachment_size": str(getattr(msg, "dmAttachmentSize", "")),
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
        status_code = str(getattr(response.dmStatus, "dmStatusCode", ""))
        if status_code != "0000":
            status_msg = str(getattr(response.dmStatus, "dmStatusMessage", ""))
            logger.error(f"ISDS error: {status_code} - {status_msg}")
            return []

        records = getattr(response, "dmRecord", None)
        if records is None:
            return []

        return [_serialize_message(msg) for msg in records]
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
        status_code = str(getattr(response.dmStatus, "dmStatusCode", ""))
        if status_code != "0000":
            status_msg = str(getattr(response.dmStatus, "dmStatusMessage", ""))
            logger.error(f"ISDS error: {status_code} - {status_msg}")
            return []

        records = getattr(response, "dmRecord", None)
        if records is None:
            return []

        return [_serialize_message(msg) for msg in records]
    except Exception as e:
        logger.error(f"list_sent failed for {box.alias}: {e}")
        raise


def read_message(box: BoxConfig, message_id: str) -> dict:
    """Download a message with attachments."""
    client = _get_operations_client(box)
    try:
        response = client.service.MessageDownload(dmID=message_id)
        status_code = str(getattr(response.dmStatus, "dmStatusCode", ""))
        if status_code != "0000":
            status_msg = str(getattr(response.dmStatus, "dmStatusMessage", ""))
            raise RuntimeError(f"ISDS error: {status_code} - {status_msg}")

        dm_return = response.dmReturnedMessage
        envelope = getattr(dm_return, "dmDm", None)
        files_container = getattr(dm_return, "dmFiles", None)

        result = _serialize_message(envelope) if envelope else {"id": message_id}

        attachments = []
        if files_container:
            file_list = getattr(files_container, "dmFile", [])
            if file_list is None:
                file_list = []
            for f in file_list:
                content = getattr(f, "dmEncodedContent", None)
                attachments.append({
                    "filename": str(getattr(f, "_dmFileDescr", "unknown")),
                    "mime_type": str(getattr(f, "_dmMimeType", "application/octet-stream")),
                    "size_bytes": len(base64.b64decode(content)) if content else 0,
                    "content_base64": str(content) if content else None,
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
        owner_info_type = client.get_type("ns3:dbOwnerInfo")

        # Try to detect query type
        if query.isdigit() and len(query) == 8:
            # ICO
            search = owner_info_type(ic=query)
        elif len(query) == 7 and query.isalnum():
            # Looks like a box ID
            search = owner_info_type(dbID=query)
        else:
            # Company/person name
            search = owner_info_type(firmName=query)

        response = client.service.FindDataBox(dbOwnerInfo=search)
        status_code = str(getattr(response.dbStatus, "dbStatusCode", ""))

        if status_code != "0000":
            status_msg = str(getattr(response.dbStatus, "dbStatusMessage", ""))
            logger.warning(f"Search returned: {status_code} - {status_msg}")
            return []

        results = getattr(response, "dbResults", None)
        if results is None:
            return []

        owner_list = getattr(results, "dbOwnerInfo", [])
        if owner_list is None:
            return []

        return [
            {
                "box_id": str(getattr(o, "dbID", "")),
                "type": str(getattr(o, "dbType", "")),
                "ico": str(getattr(o, "ic", "")),
                "firm_name": str(getattr(o, "firmName", "")),
                "first_name": str(getattr(o, "pnFirstName", "")),
                "last_name": str(getattr(o, "pnLastName", "")),
                "city": str(getattr(o, "adCity", "")),
                "street": str(getattr(o, "adStreet", "")),
                "zip": str(getattr(o, "adZipCode", "")),
                "state": str(getattr(o, "dbState", "")),
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
        status_code = str(getattr(response.dmStatus, "dmStatusCode", ""))
        return status_code == "0000"
    except Exception as e:
        logger.error(f"mark_read failed for {box.alias}/{message_id}: {e}")
        raise
