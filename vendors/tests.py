from django.test import TestCase
from core.models import Wedding
from vendors.models import VendorCandidate

class VendorWeightedScoreTests(TestCase):
    def setUp(self):
        self.wedding = Wedding.objects.create(
            groom_name='Budi',
            bride_name='Ani',
            total_budget=100000000
        )

    def test_weighted_score_is_integer(self):
        vendor = VendorCandidate.objects.create(
            wedding=self.wedding,
            name='Luxury Catering',
            category='catering',
            score_price=4,
            score_quality=5,
            score_facility=4,
            score_reputation=4,
            weight_price=35,
            weight_quality=30,
            weight_facility=20,
            weight_reputation=15,
        )
        # raw calculation:
        # (4/5 * 35) + (5/5 * 30) + (4/5 * 20) + (4/5 * 15)
        # = 28 + 30 + 16 + 12 = 86
        self.assertIsInstance(vendor.weighted_total_score, int)
        self.assertEqual(vendor.weighted_total_score, 86)
        self.assertEqual(vendor.weighted_total_score_db, 86)
