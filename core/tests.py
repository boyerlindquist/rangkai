"""
Automated test suite for Role Management, WO Multi-Workspace, Couple Privacy Isolation,
Platform Admin ALL access, and Simulated Checkout.
"""
from django.test import TestCase, Client, override_settings
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


@override_settings(SUMOPOD_API_KEY='', SUMOPOD_TEST_AMOUNT=0)
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

        # Switch to w1 (by default allow_wo_budget_access is False!)
        self.assertFalse(w1.allow_wo_budget_access)
        resp = self.client.get(reverse('core:switch_workspace', args=[w1.pk]))
        self.assertRedirects(resp, reverse('core:dashboard'))

        # WO Manager MUST be blocked (403) from private Savings Tracker
        resp_savings = self.client.get(reverse('finances:savings_tracker'))
        self.assertEqual(resp_savings.status_code, 403)

        # WO Manager ALWAYS has access to Vendors directory even when budget is locked
        self.assertEqual(self.client.get(reverse('vendors:compare')).status_code, 200)

        # By default (locked), GET /budgets/ renders friendly locked page; POST mutation returns 403
        resp_budget_locked = self.client.get(reverse('finances:dashboard'))
        self.assertEqual(resp_budget_locked.status_code, 200)
        self.assertContains(resp_budget_locked, 'Memerlukan Izin Akses')
        self.assertEqual(self.client.post(reverse('finances:add_item'), {}).status_code, 403)

        # Settings form hides total_budget from WO Manager while locked
        resp_settings = self.client.get(reverse('core:settings'))
        self.assertNotContains(resp_settings, 'name="total_budget"')

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

        # Couple toggles WO budget access ON -> WO Manager can now access /budgets/
        c_spouse1.post(reverse('core:toggle_wo_privacy'))
        w1.refresh_from_db()
        self.assertTrue(w1.allow_wo_budget_access)

        resp_budget_unlocked = self.client.get(reverse('finances:dashboard'))
        self.assertEqual(resp_budget_unlocked.status_code, 200)
        self.assertNotContains(resp_budget_unlocked, 'Memerlukan Izin Akses')

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

    def test_qa_regression_fixes(self):
        """Verify QA fixes: YYYY-MM-DD date rendering, invite preview, and clean vendor form."""
        import datetime
        u = User.objects.create_user(username='qa_fix_owner', password='password123')
        AccountProfile.objects.create(user=u, account_type='couple', project_quota=1)
        w = Wedding.objects.create(
            groom_name='Raka',
            bride_name='Sinta',
            wedding_date=datetime.date(2026, 12, 20),
        )
        WeddingMembership.objects.create(user=u, wedding=w, role='owner')
        inv = WorkspaceInvitation.objects.create(wedding=w, role='co_owner', max_uses=1, created_by=u)

        # 1. Settings renders HTML5 date value as YYYY-MM-DD (never blank!)
        self.client.login(username='qa_fix_owner', password='password123')
        resp_settings = self.client.get(reverse('core:settings'))
        self.assertContains(resp_settings, 'value="2026-12-20"')

        # 2. Vendor form hides raw English weight labels and shows (1-5) scale
        resp_vendors = self.client.get(reverse('vendors:compare'))
        self.assertNotContains(resp_vendors, 'Weight price')
        self.assertContains(resp_vendors, 'Skor Harga (1-5)')

        # 3. Adding vendor with category & 1-5 scores succeeds cleanly
        resp_add = self.client.post(reverse('vendors:add'), {
            'name': 'Catering Berkah',
            'category': 'catering',
            'price_estimate': '45000000',
            'status': 'shortlist',
            'score_price': '4',
            'score_quality': '5',
            'score_facility': '4',
            'score_reputation': '5',
        })
        self.assertRedirects(resp_add, reverse('vendors:compare'))
        self.assertContains(self.client.get(reverse('vendors:compare')), 'Catering Berkah')

        # 4. Register join page shows invite preview banner with workspace name & role
        c_guest = Client()
        resp_reg = c_guest.get(f"{reverse('core:register')}?mode=join&code={inv.code}")
        self.assertContains(resp_reg, 'Raka &amp; Sinta')
        self.assertContains(resp_reg, 'Co-Owner')

    def test_cross_tenant_idor_isolation(self):
        """Ensure User A (Workspace A) gets 404 when attempting IDOR mutations on Workspace B objects."""
        import datetime
        from finances.models import BudgetCategory, BudgetItem, SavingsGoal, SavingsDeposit
        from vendors.models import VendorCandidate
        from guests.models import Guest
        from operations.models import TaskMilestone

        # Workspace A + Owner A
        ua = User.objects.create_user(username='idor_owner_a', password='password123')
        AccountProfile.objects.create(user=ua, account_type='couple', project_quota=1)
        wa = Wedding.objects.create(groom_name='A1', bride_name='A2')
        WeddingMembership.objects.create(user=ua, wedding=wa, role='owner')

        # Workspace B + Owner B + Objects
        ub = User.objects.create_user(username='idor_owner_b', password='password123')
        AccountProfile.objects.create(user=ub, account_type='couple', project_quota=1)
        wb = Wedding.objects.create(groom_name='B1', bride_name='B2')
        mb = WeddingMembership.objects.create(user=ub, wedding=wb, role='owner')
        inv_b = WorkspaceInvitation.objects.create(wedding=wb, role='crew', created_by=ub)

        cat_b = BudgetCategory.objects.create(wedding=wb, name='Cat B', allocation_percentage=20)
        item_b = BudgetItem.objects.create(wedding=wb, category=cat_b, name='Secret Item B', actual_cost=10000000)
        goal_b = SavingsGoal.objects.create(wedding=wb, target_amount=50000000)
        dep_b = SavingsDeposit.objects.create(goal=goal_b, amount=5000000, date=datetime.date.today(), depositor='B1')
        vendor_b = VendorCandidate.objects.create(wedding=wb, name='Vendor B', category='catering')
        guest_b = Guest.objects.create(wedding=wb, name='Tamu B')
        task_b = TaskMilestone.objects.create(wedding=wb, phase='d30', title='Task B')

        # Login as Owner A and attempt IDOR across EVERY module against Workspace B IDs
        self.client.login(username='idor_owner_a', password='password123')

        idor_posts = [
            reverse('finances:delete_item', args=[item_b.pk]),
            reverse('finances:delete_category', args=[cat_b.pk]),
            reverse('finances:delete_savings_deposit', args=[dep_b.pk]),
            reverse('vendors:delete', args=[vendor_b.pk]),
            reverse('guests:delete', args=[guest_b.pk]),
            reverse('operations-checklist:toggle_task', args=[task_b.pk]),
            reverse('core:manage_member', args=[mb.pk]),
            reverse('core:revoke_invitation', args=[inv_b.pk]),
        ]
        for url in idor_posts:
            resp = self.client.post(url, {'action': 'remove'})
            self.assertEqual(resp.status_code, 404, f'IDOR failed on {url}: got {resp.status_code}')

        # Verify zero Workspace B objects were modified or deleted
        self.assertTrue(BudgetItem.objects.filter(pk=item_b.pk).exists())
        self.assertTrue(SavingsDeposit.objects.filter(pk=dep_b.pk).exists())
        self.assertTrue(VendorCandidate.objects.filter(pk=vendor_b.pk).exists())
        self.assertTrue(Guest.objects.filter(pk=guest_b.pk).exists())
        self.assertTrue(WeddingMembership.objects.filter(pk=mb.pk).exists())
        self.assertTrue(WorkspaceInvitation.objects.get(pk=inv_b.pk).is_active)

    def test_business_edge_cases_quota_join_and_excel(self):
        """Test WO full quota rejection, logged-in couple max-1 join block, multi-project crew switcher, and guest Excel download."""
        # 1. WO Manager with quota = 2
        wo = User.objects.create_user(username='edge_wo', password='password123')
        AccountProfile.objects.create(user=wo, account_type='wo_manager', organization_name='Edge WO', project_quota=2)
        self.client.login(username='edge_wo', password='password123')

        for g, b in [('P1', 'W1'), ('P2', 'W2')]:
            self.client.post(reverse('core:wo_create_project'), {'groom_name': g, 'bride_name': b, 'budget_style': 'balanced'})
        self.assertEqual(Wedding.objects.filter(managed_by=wo).count(), 2)

        # 3rd project MUST be rejected due to full quota (2/2)
        resp_3rd = self.client.post(reverse('core:wo_create_project'), {'groom_name': 'P3', 'bride_name': 'W3', 'budget_style': 'balanced'}, follow=True)
        self.assertEqual(Wedding.objects.filter(managed_by=wo).count(), 2)
        self.assertContains(resp_3rd, 'sudah penuh')

        w1, w2 = list(Wedding.objects.filter(managed_by=wo).order_by('pk'))
        inv_owner_w2 = WorkspaceInvitation.objects.get(wedding=w2, role='owner')
        inv_crew_w1 = WorkspaceInvitation.objects.get(wedding=w1, role='crew')
        inv_crew_w2 = WorkspaceInvitation.objects.get(wedding=w2, role='crew')

        # 2. Logged-in Couple Owner tries to join 2nd wedding via /join/ -> rejected!
        u_couple = User.objects.create_user(username='edge_couple', password='password123')
        AccountProfile.objects.create(user=u_couple, account_type='couple', project_quota=1)
        WeddingMembership.objects.create(user=u_couple, wedding=w1, role='owner')
        c_couple = Client()
        c_couple.login(username='edge_couple', password='password123')
        resp_join_2nd = c_couple.post(reverse('core:join_workspace'), {'invite_code': inv_owner_w2.code})
        self.assertContains(resp_join_2nd, 'hanya bisa memiliki 1 workspace')
        self.assertEqual(WeddingMembership.objects.filter(user=u_couple).count(), 1)

        # 3. Logged-in Crew joins 2 projects -> succeeds & Workspace Switcher appears!
        u_crew = User.objects.create_user(username='edge_crew', password='password123')
        AccountProfile.objects.create(user=u_crew, account_type='crew', project_quota=0)
        c_crew = Client()
        c_crew.login(username='edge_crew', password='password123')
        c_crew.post(reverse('core:join_workspace'), {'invite_code': inv_crew_w1.code})
        c_crew.post(reverse('core:join_workspace'), {'invite_code': inv_crew_w2.code})
        self.assertEqual(WeddingMembership.objects.filter(user=u_crew).count(), 2)
        resp_crew_dash = c_crew.get(reverse('core:dashboard'))
        self.assertContains(resp_crew_dash, 'ui-ws-switcher')

        # 4. Guest Excel template download works for Owner & WO Manager, blocked (403) for Crew
        resp_tpl_couple = c_couple.get(reverse('guests:download_template'))
        self.assertEqual(resp_tpl_couple.status_code, 200)
        self.assertIn('spreadsheetml', resp_tpl_couple['Content-Type'])

        self.client.get(reverse('core:switch_workspace', args=[w1.pk]))
        resp_tpl_wo = self.client.get(reverse('guests:download_template'))
        self.assertEqual(resp_tpl_wo.status_code, 200)

        resp_tpl_crew = c_crew.get(reverse('guests:download_template'))
        self.assertEqual(resp_tpl_crew.status_code, 403)

    def test_password_reset_and_change_flows(self):
        """Test self-service email password reset, logged-in password change, and Admin Console password reset."""
        from django.core import mail
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        u = User.objects.create_user(username='pwd_user', email='pwd_user@example.com', password='oldpassword123')
        AccountProfile.objects.create(user=u, account_type='couple', project_quota=1)
        w = Wedding.objects.create(groom_name='G', bride_name='B')
        WeddingMembership.objects.create(user=u, wedding=w, role='owner')

        # 1. Self-service password reset request sends email with valid token
        resp_req = self.client.post(reverse('core:password_reset'), {'email': 'pwd_user@example.com'})
        self.assertRedirects(resp_req, reverse('core:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Rangkai.click', mail.outbox[0].subject)

        uid = urlsafe_base64_encode(force_bytes(u.pk))
        token = default_token_generator.make_token(u)
        confirm_url = reverse('core:password_reset_confirm', args=[uid, token])
        # Django's PasswordResetConfirmView redirects to set-password session token first
        resp_get = self.client.get(confirm_url, follow=True)
        self.assertEqual(resp_get.status_code, 200)
        resp_post = self.client.post(resp_get.request['PATH_INFO'], {
            'new_password1': 'newpass12345',
            'new_password2': 'newpass12345',
        })
        self.assertRedirects(resp_post, reverse('core:password_reset_complete'))
        u.refresh_from_db()
        self.assertTrue(u.check_password('newpass12345'))

        # 2. Logged-in user changes own password via /account/password/
        self.client.login(username='pwd_user', password='newpass12345')
        resp_chg = self.client.post(reverse('core:change_password'), {
            'old_password': 'newpass12345',
            'new_password1': 'changedpass99',
            'new_password2': 'changedpass99',
        })
        self.assertRedirects(resp_chg, reverse('core:change_password'))
        u.refresh_from_db()
        self.assertTrue(u.check_password('changedpass99'))

        # 3. Platform Admin resets user password from Admin Console
        adm = User.objects.create_user(username='pwd_admin', password='adminpass123', is_staff=True, is_superuser=True)
        AccountProfile.objects.create(user=adm, account_type='admin', project_quota=0)
        c_adm = Client()
        c_adm.login(username='pwd_admin', password='adminpass123')
        resp_adm = c_adm.post(reverse('core:admin_console'), {
            'action': 'reset_password',
            'user_id': u.pk,
            'new_password': 'adminreset888',
        })
        self.assertRedirects(resp_adm, reverse('core:admin_console'))
        u.refresh_from_db()
        self.assertTrue(u.check_password('adminreset888'))


class SumopodPaymentTests(TestCase):
    """End-to-end tests for Sumopod QRIS checkout, API status polling, and webhooks."""

    @staticmethod
    def _make_svix_sig(secret, svix_id, svix_ts, raw_body):
        import base64
        import hashlib
        import hmac
        clean = secret[6:] if secret.startswith('whsec_') else secret
        secret_bytes = base64.b64decode(clean)
        signed = f'{svix_id}.{svix_ts}.{raw_body}'.encode('utf-8')
        digest = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode('utf-8')
        return f'v1,{digest}'

    def test_sumopod_checkout_and_api_polling_activation(self):
        from datetime import timedelta
        from unittest.mock import patch
        from django.test import override_settings
        from django.utils import timezone
        from core.models import Order

        mock_create_resp = {
            'payment_id': 'pay-uuid-1234',
            'order_id': 'RNK-MOCK',
            'amount': 149000,
            'fee': 1343,
            'net_amount': 147657,
            'payment_link_url': 'https://pay-sandbox.sumopod.com/pay/pay-uuid-1234',
            'payment_code': '',
            'status': 'pending',
            'expires_at': timezone.now() + timedelta(hours=24),
            'raw': {},
        }

        with override_settings(SUMOPOD_API_KEY='sk_sandbox_test'):
            with patch('core.services.sumopod.create_payment', return_value=mock_create_resp) as m_create:
                resp = self.client.post(reverse('core:checkout'), {
                    'plan_type': 'wedding_owner',
                    'username': 'sumo_couple',
                    'email': 'sumo@example.com',
                    'password': 'password123',
                    'password_confirm': 'password123',
                    'groom_name': 'Raka',
                    'bride_name': 'Sinta',
                    'payment_method': 'qris',
                })
                m_create.assert_called_once()

            order = Order.objects.get(user__username='sumo_couple')
            self.assertEqual(order.status, 'pending')
            self.assertEqual(order.gateway_ref, 'pay-uuid-1234')
            self.assertEqual(order.payment_link_url, 'https://pay-sandbox.sumopod.com/pay/pay-uuid-1234')
            self.assertEqual(order.user.profile.plan_status, 'pending')
            self.assertRedirects(resp, reverse('core:checkout_pay', kwargs={'order_code': order.order_code}))

            # Native Rangkai payment page renders embedded QRIS link
            pay_page = self.client.get(reverse('core:checkout_pay', kwargs={'order_code': order.order_code}))
            self.assertEqual(pay_page.status_code, 200)
            self.assertContains(pay_page, 'https://pay-sandbox.sumopod.com/pay/pay-uuid-1234')

            # API polling detects completed payment & provisions Wedding workspace
            mock_status_resp = {
                'payment_id': 'pay-uuid-1234',
                'order_id': order.order_code,
                'amount': 149000,
                'fee': 1343,
                'net_amount': 147657,
                'status': 'completed',
                'paid_at': timezone.now(),
                'raw': {},
            }
            with patch('core.services.sumopod.get_payment_status', return_value=mock_status_resp):
                poll_resp = self.client.get(
                    reverse('core:checkout_pay_status', kwargs={'order_code': order.order_code})
                )
            self.assertEqual(poll_resp.status_code, 200)
            payload = poll_resp.json()
            self.assertTrue(payload['paid'])

            order.refresh_from_db()
            self.assertEqual(order.status, 'paid')
            order.user.profile.refresh_from_db()
            self.assertEqual(order.user.profile.plan_status, 'active')
            self.assertEqual(WeddingMembership.objects.filter(user=order.user, role='owner').count(), 1)

            # Visiting checkout_pay auto-logs buyer in and redirects to dashboard
            done_resp = self.client.get(reverse('core:checkout_pay', kwargs={'order_code': order.order_code}))
            self.assertRedirects(done_resp, reverse('core:dashboard'))

    def test_sumopod_checkout_error_rolls_back_user(self):
        from unittest.mock import patch
        from django.test import override_settings
        from core.services.sumopod import SumopodError

        with override_settings(SUMOPOD_API_KEY='sk_sandbox_test'):
            with patch('core.services.sumopod.create_payment', side_effect=SumopodError('Gateway timeout')):
                resp = self.client.post(reverse('core:checkout'), {
                    'plan_type': 'wo_manager',
                    'username': 'rollback_wo',
                    'email': 'rollback@example.com',
                    'password': 'password123',
                    'password_confirm': 'password123',
                    'organization_name': 'Rollback WO',
                    'payment_method': 'qris',
                })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='rollback_wo').exists())

    def test_sumopod_webhook_token_svix_isolation_and_idempotency(self):
        import base64
        import json
        from django.test import override_settings
        from core.models import Order

        user = User.objects.create_user(username='wh_buyer', email='wh@example.com', password='password123')
        AccountProfile.objects.create(user=user, account_type='couple', project_quota=0, plan_status='pending')
        order = Order.objects.create(
            user=user,
            customer_email=user.email,
            plan_type='wedding_owner',
            amount=149000,
            payment_method='qris',
            status='pending',
            gateway_ref='pay-wh-999',
            metadata={'groom_name': 'Budi', 'bride_name': 'Ayu', 'wedding_date': '2027-05-10'},
        )

        secret_b64 = base64.b64encode(b'super-secret-svix-key-32-bytes!!').decode('utf-8')
        whsec = f'whsec_{secret_b64}'
        webhook_url = reverse('core:sumopod_webhook')

        with override_settings(
            SUMOPOD_WEBHOOK_TOKEN='whtok_test_123',
            SUMOPOD_WEBHOOK_SECRET=whsec,
            SUMOPOD_FORWARD_WEBHOOK_URL='',
        ):
            # 1. Invalid token/signature rejected with 401
            r_bad = self.client.post(
                webhook_url,
                data=json.dumps({'event_type': 'payment.test'}),
                content_type='application/json',
                HTTP_X_WEBHOOK_TOKEN='wrong_token',
            )
            self.assertEqual(r_bad.status_code, 401)

            # 2. Valid X-Webhook-Token + payment.test returns 200
            r_test = self.client.post(
                webhook_url,
                data=json.dumps({'event_type': 'payment.test', 'data': {}}),
                content_type='application/json',
                HTTP_X_WEBHOOK_TOKEN='whtok_test_123',
            )
            self.assertEqual(r_test.status_code, 200)
            self.assertTrue(r_test.json()['ok'])

            # 3. Non-RNK order (e.g. TickerWatch) is safely ignored with 200
            r_tw = self.client.post(
                webhook_url,
                data=json.dumps({
                    'event_type': 'payment.completed',
                    'data': {'payment_id': 'pay-tw-1', 'order_id': 'TW-2026-001', 'amount': 50000},
                }),
                content_type='application/json',
                HTTP_X_WEBHOOK_TOKEN='whtok_test_123',
            )
            self.assertEqual(r_tw.status_code, 200)
            self.assertTrue(r_tw.json()['ignored'])
            self.assertEqual(r_tw.json()['reason'], 'non_rangkai_order')

            # 4. Valid Svix HMAC signature completes order & provisions Wedding idempotently
            completed_body = json.dumps({
                'event_type': 'payment.completed',
                'data': {
                    'payment_id': 'pay-wh-999',
                    'order_id': order.order_code,
                    'amount': 149000,
                    'fee': 1343,
                    'net_amount': 147657,
                    'status': 'completed',
                    'paid_at': '2026-11-20T06:00:00Z',
                },
            })
            svix_id = 'msg_test_001'
            svix_ts = '1763618400'
            svix_sig = self._make_svix_sig(whsec, svix_id, svix_ts, completed_body)

            r_ok1 = self.client.post(
                webhook_url,
                data=completed_body,
                content_type='application/json',
                HTTP_SVIX_ID=svix_id,
                HTTP_SVIX_TIMESTAMP=svix_ts,
                HTTP_SVIX_SIGNATURE=svix_sig,
            )
            self.assertEqual(r_ok1.status_code, 200)
            self.assertEqual(r_ok1.json()['status'], 'paid')

            # Re-sending same webhook is idempotent (still 1 Wedding, no crash)
            r_ok2 = self.client.post(
                webhook_url,
                data=completed_body,
                content_type='application/json',
                HTTP_X_WEBHOOK_TOKEN='whtok_test_123',
            )
            self.assertEqual(r_ok2.status_code, 200)
            order.refresh_from_db()
            self.assertEqual(order.status, 'paid')
            self.assertEqual(order.gateway_fee, 1343)
            self.assertEqual(WeddingMembership.objects.filter(user=user, role='owner').count(), 1)

    def test_unpaid_user_cannot_login_redirected_to_select_plan_and_can_repay(self):
        from datetime import timedelta
        from unittest.mock import patch
        from django.test import override_settings
        from django.utils import timezone
        from core.models import Order

        # 1. Unpaid user with active pending QRIS order -> redirected to /checkout/select-plan/
        u1 = User.objects.create_user(username='unpaid_1', email='u1@example.com', password='password123')
        AccountProfile.objects.create(user=u1, account_type='couple', project_quota=0, plan_status='pending')
        o1 = Order.objects.create(
            user=u1,
            customer_email=u1.email,
            plan_type='wedding_owner',
            amount=149000,
            payment_method='qris',
            status='pending',
            payment_link_url='https://checkout.pymnt.app/payment-links/test-active',
            expires_at=timezone.now() + timedelta(hours=12),
            metadata={'groom_name': 'Aldi', 'bride_name': 'Rani'},
        )
        r1 = self.client.post(reverse('core:login'), {'username': 'unpaid_1', 'password': 'password123'})
        self.assertRedirects(r1, reverse('core:checkout_select_plan'))
        self.assertNotIn('_auth_user_id', self.client.session)

        # Dedicated select-plan page shows resume banner for active pending QRIS
        sp_get = self.client.get(reverse('core:checkout_select_plan'))
        self.assertEqual(sp_get.status_code, 200)
        self.assertContains(sp_get, o1.order_code)

        # Submitting select-plan generates a fresh QRIS order & cancels the old pending order
        mock_create_resp = {
            'payment_id': 'pay-uuid-fresh',
            'order_id': 'RNK-FRESH',
            'amount': 499000,
            'fee': 3793,
            'net_amount': 495207,
            'payment_link_url': 'https://checkout.pymnt.app/payment-links/fresh-wo',
            'payment_code': '',
            'status': 'pending',
            'expires_at': timezone.now() + timedelta(hours=24),
            'raw': {},
        }
        with override_settings(SUMOPOD_API_KEY='sk_live_test'):
            with patch('core.services.sumopod.create_payment', return_value=mock_create_resp):
                sp_post = self.client.post(reverse('core:checkout_select_plan'), {
                    'plan_type': 'wo_manager',
                    'organization_name': 'Aldi Events WO',
                })
        o1.refresh_from_db()
        self.assertEqual(o1.status, 'cancelled')
        new_order = Order.objects.filter(user=u1, status='pending').first()
        self.assertIsNotNone(new_order)
        self.assertEqual(new_order.plan_type, 'wo_manager')
        self.assertRedirects(sp_post, reverse('core:checkout_pay', kwargs={'order_code': new_order.order_code}))

        # 2. Admin Console manual "Tandai Lunas" activates pending order & profile
        adm = User.objects.create_user(username='pay_admin', password='adminpass123', is_staff=True, is_superuser=True)
        AccountProfile.objects.create(user=adm, account_type='admin', project_quota=0)
        c_adm = Client()
        c_adm.login(username='pay_admin', password='adminpass123')
        r_mark = c_adm.post(reverse('core:admin_console'), {
            'action': 'mark_order_paid',
            'order_id': new_order.pk,
        })
        self.assertRedirects(r_mark, reverse('core:admin_console'))
        new_order.refresh_from_db()
        self.assertEqual(new_order.status, 'paid')
        u1.profile.refresh_from_db()
        self.assertEqual(u1.profile.plan_status, 'active')
        self.assertEqual(u1.profile.account_type, 'wo_manager')

    def test_sumopod_webhook_forwards_non_rangkai_orders_when_configured(self):
        import json
        from unittest.mock import patch
        from django.test import override_settings

        webhook_url = reverse('core:sumopod_webhook')
        tw_payload = json.dumps({
            'event_type': 'payment.completed',
            'data': {'payment_id': 'pay-tw-99', 'order_id': 'TW-2026-099', 'amount': 50000},
        })
        with override_settings(
            SUMOPOD_WEBHOOK_TOKEN='whtok_fwd_123',
            SUMOPOD_FORWARD_WEBHOOK_URL='https://tickerwatch.example.com/webhooks/sumopod',
        ):
            with patch('core.services.sumopod.forward_webhook', return_value=(200, '{"ok":true}')) as m_fwd:
                resp = self.client.post(
                    webhook_url,
                    data=tw_payload,
                    content_type='application/json',
                    HTTP_X_WEBHOOK_TOKEN='whtok_fwd_123',
                )
                m_fwd.assert_called_once()
                call_args = m_fwd.call_args[0]
                self.assertEqual(call_args[0], 'https://tickerwatch.example.com/webhooks/sumopod')
                self.assertEqual(call_args[2], tw_payload.encode('utf-8'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['forwarded'])

    def test_authenticated_pages_send_no_store_cache_headers(self):
        u = User.objects.create_user(username='cache_user', password='password123')
        AccountProfile.objects.create(user=u, account_type='couple', project_quota=1, plan_status='active')
        w = Wedding.objects.create(groom_name='A', bride_name='B')
        WeddingMembership.objects.create(user=u, wedding=w, role='owner')
        self.client.login(username='cache_user', password='password123')
        resp = self.client.get(reverse('core:dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('no-store', resp.headers.get('Cache-Control', ''))
        self.assertEqual(resp.headers.get('Pragma'), 'no-cache')

    def test_register_cannot_bypass_checkout_paywall(self):
        # Direct GET /register/ without invite mode/code redirects to /checkout/
        r_get = self.client.get(reverse('core:register'))
        self.assertRedirects(r_get, reverse('core:checkout'))

        # Direct POST /register/ with mode=create is blocked and redirected to /checkout/
        r_post = self.client.post(reverse('core:register'), {
            'mode': 'create',
            'username': 'free_bypass',
            'email': 'free@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'groom_name': 'Free',
            'bride_name': 'Bypass',
        })
        self.assertRedirects(r_post, reverse('core:checkout'))
        self.assertFalse(User.objects.filter(username='free_bypass').exists())

        # Invite-code registration (/register/?mode=join) still works cleanly
        r_join = self.client.get(reverse('core:register') + '?mode=join')
        self.assertEqual(r_join.status_code, 200)
