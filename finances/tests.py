from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import datetime
import json
from core.models import Wedding, WeddingMembership
from finances.models import BudgetCategory, BudgetItem, SavingsGoal, SavingsDeposit

class SavingsTrackerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.wedding = Wedding.objects.create(
            groom_name='Budi',
            bride_name='Ani',
            wedding_date=datetime.date.today() + datetime.timedelta(days=180),
            total_budget=100000000
        )
        WeddingMembership.objects.create(
            wedding=self.wedding,
            user=self.user,
            role='owner'
        )
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_savings_tracker_empty_chart(self):
        goal = SavingsGoal.objects.create(
            wedding=self.wedding,
            target_amount=50000000,
            monthly_deposit=5000000
        )
        response = self.client.get(reverse('finances:savings_tracker'))
        self.assertEqual(response.status_code, 200)
        chart_data = response.context['chart_data']
        self.assertFalse(chart_data['has_data'])
        self.assertEqual(chart_data['target_amount'], 50000000)

    def test_savings_tracker_cumulative_chart(self):
        goal = SavingsGoal.objects.create(
            wedding=self.wedding,
            target_amount=50000000,
            monthly_deposit=5000000
        )
        SavingsDeposit.objects.create(
            goal=goal,
            amount=5000000,
            date=datetime.date(2025, 1, 10),
            depositor='CPP'
        )
        SavingsDeposit.objects.create(
            goal=goal,
            amount=3000000,
            date=datetime.date(2025, 1, 15),
            depositor='CPW'
        )
        SavingsDeposit.objects.create(
            goal=goal,
            amount=4000000,
            date=datetime.date(2025, 2, 1),
            depositor='CPP'
        )

        response = self.client.get(reverse('finances:savings_tracker'))
        self.assertEqual(response.status_code, 200)
        chart_data = response.context['chart_data']
        self.assertTrue(chart_data['has_data'])
        self.assertEqual(chart_data['target_amount'], 50000000)
        self.assertIn('CPP', chart_data['depositors'])
        self.assertIn('CPW', chart_data['depositors'])
        
        # Check cumulative total series: [0, 5M, 8M, 12M]
        self.assertEqual(chart_data['total_series'], [0, 5000000, 8000000, 12000000])
        # Check CPP cumulative series: [0, 5M, 5M, 9M]
        self.assertEqual(chart_data['depositor_series']['CPP'], [0, 5000000, 5000000, 9000000])
        # Check CPW cumulative series: [0, 0, 3M, 3M]
        self.assertEqual(chart_data['depositor_series']['CPW'], [0, 0, 3000000, 3000000])
        # Check Target line series is constant 50M
        self.assertEqual(chart_data['target_series'], [50000000, 50000000, 50000000, 50000000])

    def test_delete_deposit(self):
        goal = SavingsGoal.objects.create(
            wedding=self.wedding,
            target_amount=50000000
        )
        deposit = SavingsDeposit.objects.create(
            goal=goal,
            amount=5000000,
            date=datetime.date(2025, 1, 10),
            depositor='CPP'
        )
        response = self.client.post(reverse('finances:delete_savings_deposit', kwargs={'pk': deposit.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SavingsDeposit.objects.count(), 0)

    def test_sankey_static_target_and_unused_branch_on_category_delete(self):
        SavingsGoal.objects.create(
            wedding=self.wedding,
            target_amount=100000000,
            monthly_deposit=5000000
        )
        cat_catering = BudgetCategory.objects.create(
            wedding=self.wedding,
            name='Catering & F&B',
            allocated_budget=95000000,
            allocation_percentage=95
        )
        cat_ent = BudgetCategory.objects.create(
            wedding=self.wedding,
            name='Entertainment & MC',
            allocated_budget=5000000,
            allocation_percentage=5
        )

        # Delete Entertainment (5 juta)
        del_res = self.client.post(reverse('finances:delete_category', kwargs={'pk': cat_ent.pk}))
        self.assertEqual(del_res.status_code, 302)

        # Load budget dashboard and inspect sankey data
        res = self.client.get(reverse('finances:dashboard'))
        self.assertEqual(res.status_code, 200)
        sankey_data = json.loads(res.context['sankey_data_json'])
        sankey_meta = json.loads(res.context['sankey_meta_json'])

        # 1. Source is 'Total Tabungan (Target)' with static 100M
        self.assertEqual(sankey_meta['source_node'], 'Total Tabungan (Target)')
        self.assertEqual(sankey_meta['target_budget'], 100000000)
        self.assertEqual(sankey_meta['unused_amount'], 5000000)

        # 2. Layer 1 links from 'Total Tabungan (Target)' sum to static 100M and include 'Belum Dialokasikan (Unused)' = 5M
        layer1_links = [d for d in sankey_data if d['layer'] == 1 and d['from'] == 'Total Tabungan (Target)']
        self.assertEqual(sum(d['weight'] for d in layer1_links), 100000000)
        unused_links = [d for d in layer1_links if d['to'] == 'Belum Dialokasikan (Unused)']
        self.assertEqual(len(unused_links), 1)
        self.assertEqual(unused_links[0]['weight'], 5000000)

