"""Tests for base64 encoding compatibility (Gmail URL-safe vs standard)."""

import base64
import pytest


class TestBase64Conversion:
    """Verify that URL-safe base64 from Gmail is correctly converted."""

    def test_standard_base64_unchanged(self):
        """Standard base64 should decode correctly without conversion."""
        original = b"Hello, World!"
        encoded = base64.b64encode(original).decode()
        assert base64.b64decode(encoded) == original

    def test_urlsafe_base64_conversion(self):
        """URL-safe base64 (-_ instead of +/) should be convertible."""
        original = b"\xfb\xff\xfe"  # bytes that produce +/ in standard base64
        standard = base64.b64encode(original).decode()
        urlsafe = base64.urlsafe_b64encode(original).decode().rstrip("=")

        # Verify they differ
        assert "+" in standard or "/" in standard
        assert "+" not in urlsafe and "/" not in urlsafe

        # Apply the same conversion as isds.py
        converted = urlsafe.replace('-', '+').replace('_', '/')
        padding = 4 - len(converted) % 4
        if padding < 4:
            converted += '=' * padding

        assert base64.b64decode(converted) == original

    def test_xml_content_roundtrip(self):
        """Simulate Gmail attachment -> ISDS send roundtrip."""
        xml_content = b'<?xml version="1.0" encoding="UTF-8"?><root><data>test</data></root>'

        # Gmail returns URL-safe base64
        gmail_b64 = base64.urlsafe_b64encode(xml_content).decode().rstrip("=")

        # Our conversion in isds.py
        content = gmail_b64.replace('-', '+').replace('_', '/')
        padding = 4 - len(content) % 4
        if padding < 4:
            content += '=' * padding
        decoded = base64.b64decode(content)

        assert decoded == xml_content
        assert decoded.startswith(b'<?xml')

    def test_large_binary_roundtrip(self):
        """Test with larger binary content (simulating PDF)."""
        import os
        binary_content = os.urandom(10000)

        gmail_b64 = base64.urlsafe_b64encode(binary_content).decode().rstrip("=")

        content = gmail_b64.replace('-', '+').replace('_', '/')
        padding = 4 - len(content) % 4
        if padding < 4:
            content += '=' * padding
        decoded = base64.b64decode(content)

        assert decoded == binary_content

    def test_already_padded_base64(self):
        """Base64 with existing padding should work too."""
        original = b"test data"
        encoded = base64.b64encode(original).decode()  # Already has padding

        content = encoded.replace('-', '+').replace('_', '/')
        padding = 4 - len(content) % 4
        if padding < 4:
            content += '=' * padding
        decoded = base64.b64decode(content)

        assert decoded == original
