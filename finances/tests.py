from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import datetime
import json
from core.models import Wedding, WeddingMembership
from finances.models import SavingsGoal, SavingsDeposit

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
