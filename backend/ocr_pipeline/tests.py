from django.test import TestCase
from ocr_pipeline.normalize import normalize_state, normalize_date, _clean_bill_to_ocr_extract, get_normalized_export_record

class NormalizationPipelineTestCase(TestCase):
    def test_normalize_state_gst_numeric_code(self):
        self.assertEqual(normalize_state("33"), "Tamil Nadu")
        self.assertEqual(normalize_state("33 - Tamil Nadu"), "Tamil Nadu")
        self.assertEqual(normalize_state("29"), "Karnataka")
        self.assertEqual(normalize_state("27"), "Maharashtra")
        self.assertEqual(normalize_state("TN"), "Tamil Nadu")

    def test_clean_bill_to_ocr_extract_noise_prefix(self):
        raw_bill_to = "Invoice Details Accuturn Machiners Pvt. Ltd"
        cleaned = _clean_bill_to_ocr_extract(raw_bill_to)
        self.assertEqual(cleaned, "Accuturn Machiners Pvt. Ltd")

    def test_clean_bill_to_ocr_extract_voucher_details_prefix(self):
        raw_bill_to = "Voucher Details Accuturn Machiners Pvt. Ltd 13A Road"
        cleaned = _clean_bill_to_ocr_extract(raw_bill_to)
        self.assertEqual(cleaned, "Accuturn Machiners Pvt. Ltd 13A Road")

    def test_normalize_date_formats(self):
        self.assertEqual(normalize_date("30/09/2025"), "30-09-2025")
        self.assertEqual(normalize_date("2025-08-22"), "22-08-2025")
        self.assertEqual(normalize_date("13 Aug 2025"), "13-08-2025")

    def test_get_normalized_export_record_pos_derivation(self):
        raw_data = {
            "invoice_no": "TEST-100",
            "invoice_date": "10-09-2025",
            "place_of_supply": "33",
            "vendor_gstin": "33AACCS5981M2ZV",
            "bill_to": "Accuturn Machiners Pvt Ltd"
        }
        res = get_normalized_export_record(raw_data)
        self.assertEqual(res["place_of_supply"], "Tamil Nadu")
        self.assertEqual(res["invoice_date"], "10-09-2025")
        self.assertEqual(res["bill_to"], "Accuturn Machiners Pvt Ltd")
