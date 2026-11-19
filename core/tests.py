"""
Automated test suite for Role Management, WO Multi-Workspace, Couple Privacy Isolation,
Platform Admin ALL access, and Simulated Checkout.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from core.models import (
    AccountProfile,
    Wedding,
    WeddingMembership,
    WorkspaceInvitation,
    Order,
)


class RoleManagementAndCheckoutTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_checkout_wedding_owner_provisions_workspace(self):
        resp = self.client.post(reverse('core:checkout'), {
            'plan_type': 'wedding_owner',
            'payment_method': 'qris',
            'username': 'pengantin_a',
            'email': 'a@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'groom_name': 'Dimas',
            'bride_name': 'Nadya',
        })
        self.assertRedirects(resp, reverse('core:dashboard'))
        user = User.objects.get(username='pengantin_a')
        self.assertEqual(user.profile.account_type, 'couple')
        self.assertEqual(user.profile.project_quota, 1)
        self.assertEqual(Order.objects.filter(user=user, status='paid', plan_type='wedding_owner').count(), 1)
        membership = WeddingMembership.objects.get(user=user)
        self.assertEqual(membership.role, 'owner')

    def test_checkout_wo_manager_provisions_wo_portal(self):
        resp = self.client.post(reverse('core:checkout'), {
            'plan_type': 'wo_manager',
            'payment_method': 'va_bca',
            'username': 'wo_surya',
            'email': 'surya@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'organization_name': 'Surya Wedding Organizer',
        })
        self.assertRedirects(resp, reverse('core:wo_portal'))
        user = User.objects.get(username='wo_surya')
        self.assertEqual(user.profile.account_type, 'wo_manager')
        self.assertEqual(user.profile.organization_name, 'Surya Wedding Organizer')
        self.assertEqual(user.profile.project_quota, 10)
        self.assertEqual(Order.objects.filter(user=user, status='paid', plan_type='wo_manager').count(), 1)

    def test_couple_owner_limited_to_one_wedding(self):
        u = User.objects.create_user(username='couple1', password='password123')
        AccountProfile.objects.create(user=u, account_type='couple', project_quota=1)
        w1 = Wedding.objects.create(groom_name='A', bride_name='B')
        w2 = Wedding.objects.create(groom_name='C', bride_name='D')
        WeddingMembership.objects.create(user=u, wedding=w1, role='owner')

        with self.assertRaises(ValidationError):
            WeddingMembership.objects.create(user=u, wedding=w2, role='co_owner')

    def test_wo_multi_project_switcher_and_couple_privacy(self):
        wo = User.objects.create_user(username='wo_lead', password='password123')
        AccountProfile.objects.create(
            user=wo,
            account_type='wo_manager',
            organization_name='Atelier WO',
            project_quota=5,
        )
        self.client.login(username='wo_lead', password='password123')

        # Create 2 client projects
        for g, b in [('Budi', 'Ani'), ('Reza', 'Dina')]:
            resp = self.client.post(reverse('core:wo_create_project'), {
                'groom_name': g,
                'bride_name': b,
                'budget_style': 'balanced',
            })
            self.assertRedirects(resp, reverse('core:wo_portal'))

        self.assertEqual(Wedding.objects.filter(managed_by=wo).count(), 2)
        w1, w2 = list(Wedding.objects.filter(managed_by=wo).order_by('pk'))

        # Switch to w1
        resp = self.client.get(reverse('core:switch_workspace', args=[w1.pk]))
        self.assertRedirects(resp, reverse('core:dashboard'))

        # WO Manager MUST be blocked (403) from private Savings Tracker
        resp_savings = self.client.get(reverse('finances:savings_tracker'))
        self.assertEqual(resp_savings.status_code, 403)

        # WO Manager can access Budget & Vendors when allow_wo_budget_access=True
        self.assertEqual(self.client.get(reverse('finances:dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('vendors:compare')).status_code, 200)

        # Couple joins via generated 2-use owner invite: spouse 1 -> owner, spouse 2 -> co_owner
        couple_inv = WorkspaceInvitation.objects.get(wedding=w1, role='owner')
        self.assertEqual(couple_inv.max_uses, 2)

        c_spouse1 = Client()
        resp_join1 = c_spouse1.post(reverse('core:register'), {
            'mode': 'join',
            'username': 'budi_groom',
            'email': 'budi@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'invite_code': couple_inv.code,
        })
        self.assertRedirects(resp_join1, reverse('core:dashboard'))
        self.assertEqual(WeddingMembership.objects.get(user__username='budi_groom', wedding=w1).role, 'owner')

        # Couple CAN access Savings Tracker
        self.assertEqual(c_spouse1.get(reverse('finances:savings_tracker')).status_code, 200)

        # Couple toggles WO budget privacy OFF
        c_spouse1.post(reverse('core:toggle_wo_privacy'))
        w1.refresh_from_db()
        self.assertFalse(w1.allow_wo_budget_access)

        # Now WO Manager gets 403 on Budget & Vendors too!
        self.assertEqual(self.client.get(reverse('finances:dashboard')).status_code, 403)
        self.assertEqual(self.client.get(reverse('vendors:compare')).status_code, 403)

        # Spouse 2 joins with same invite -> becomes co_owner, then invite deactivates
        c_spouse2 = Client()
        c_spouse2.post(reverse('core:register'), {
            'mode': 'join',
            'username': 'ani_bride',
            'email': 'ani@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'invite_code': couple_inv.code,
        })
        self.assertEqual(WeddingMembership.objects.get(user__username='ani_bride', wedding=w1).role, 'co_owner')
        couple_inv.refresh_from_db()
        self.assertFalse(couple_inv.is_active)

    def test_platform_admin_has_all_access(self):
        admin_user = User.objects.create_user(
            username='super_rangkai',
            password='password123',
            is_staff=True,
            is_superuser=True,
        )
        AccountProfile.objects.create(user=admin_user, account_type='admin', project_quota=0)

        w = Wedding.objects.create(groom_name='Klien', bride_name='Privat', allow_wo_budget_access=False)

        self.client.login(username='super_rangkai', password='password123')
        self.assertEqual(self.client.get(reverse('core:admin_console')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:wo_portal')).status_code, 200)

        # Admin can inspect ANY workspace including Savings & locked Budget
        self.client.get(reverse('core:switch_workspace', args=[w.pk]))
        self.assertEqual(self.client.get(reverse('finances:savings_tracker')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finances:dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('vendors:compare')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:settings')).status_code, 200)
