import pytest
from snaglist_pro.parse_export import parse_whatsapp_text, extract_media_refs


class TestParseWhatsAppText:
    def test_parses_simple_message(self, sample_chat_text):
        messages = parse_whatsapp_text(sample_chat_text)
        assert len(messages) > 0
        assert messages[0]["sender"] == "Nasar Indiqube"
        assert "window to be rectified" in messages[0]["message"].lower()

    def test_parses_date_correctly(self, sample_chat_text):
        messages = parse_whatsapp_text(sample_chat_text)
        assert messages[0]["date"] == "2026-07-26"

    def test_handles_empty_text(self):
        messages = parse_whatsapp_text("")
        assert messages == []

    def test_handles_none_text(self):
        messages = parse_whatsapp_text(None)
        assert messages == []

    def test_detects_media_omitted(self, sample_chat_text):
        messages = parse_whatsapp_text(sample_chat_text)
        media_msgs = [m for m in messages if m.get("has_media")]
        assert len(media_msgs) > 0

    def test_extracts_media_refs(self):
        text = 'IMG-20260726-WA0001.jpg (file attached)'
        refs = extract_media_refs(text)
        assert len(refs) > 0

    def test_extracts_attached_pattern(self):
        text = '<attached: document.pdf>'
        refs = extract_media_refs(text)
        assert "document.pdf" in refs

    def test_splits_numbered_observations_in_one_message(self):
        text = (
            "[9/18/26, 6:05:10 PM] Nasar Indiqube: Fapa observation at Skyline Tower- Aisle network -2F\n"
            "1. Electrical room & Rest room fapa system to be installed.\n"
            "2. Fire exit door buzzer to be installed.\n"
            "3. Client space reception area 1 no of Fire extinguisher to be installed as per drawing.\n"
            "4. All the Fire extinguisher signage to be installed.\n"
            "5. Rest passage area detectors naming to be added as rest room passage instead of common passage.\n"
            "6. Pantry below false ceiling heat detector to be installed.\n"
            "7. Canteen AFC detector address to be changed as Pantry AFC.\n"
            "8. Music system pendrive to be handover.\n"
            "9. FA panel battery to be installed.\n"
            "10. Fire escape route plan to be installed.\n"
            "11. Isolator module to be fixed properly in 2 pax room.\n"
            "12. Server room BBF address to be changed as BFF as per report.\n"
            "13. All the common passage detector BFC naming to be removed.\n"
            "14. Common area AFC detectors to be installed.\n"
            "15. Music system demo to be given.\n"
            "16. Pressure gauge to be installed."
        )

        messages = parse_whatsapp_text(text)

        assert len(messages) == 16
        assert messages[0]["message"].startswith("Electrical room")
        assert messages[-1]["message"] == "Pressure gauge to be installed."


class TestExtractMediaRefs:
    def test_img_file_attached(self):
        text = "IMG-20260726-WA0001.jpg (file attached)"
        refs = extract_media_refs(text)
        assert "IMG-20260726-WA0001.jpg" in refs

    def test_attached_tag(self):
        text = "<attached: drawing.dwg>"
        refs = extract_media_refs(text)
        assert "drawing.dwg" in refs

    def test_media_omitted(self):
        text = "<Media omitted>"
        refs = extract_media_refs(text)
        assert "__MEDIA_OMITTED__" in refs

    def test_empty_text(self):
        refs = extract_media_refs("")
        assert refs == []

    def test_no_media(self):
        refs = extract_media_refs("Just a normal message")
        assert refs == []
