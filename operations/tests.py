from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Wedding, WeddingMembership
from operations.models import TimelinePhase, TaskMilestone


class ChecklistCustomPhasesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testbride', password='password123')
        self.wedding = Wedding.objects.create(
            groom_name='Budi',
            bride_name='Siti',
            total_budget=100_000_000,
        )
        WeddingMembership.objects.create(user=self.user, wedding=self.wedding, role='owner')
        self.client.force_login(self.user)

    def test_safe_delete_phase_moves_tasks_to_target_phase(self):
        # Load checklist to initialize default phases
        resp = self.client.get(reverse('operations-checklist:checklist'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(TimelinePhase.objects.filter(wedding=self.wedding).count(), 5)

        # Create 2 tasks in d360
        TaskMilestone.objects.create(wedding=self.wedding, phase='d360', title='Task A')
        TaskMilestone.objects.create(wedding=self.wedding, phase='d360', title='Task B')

        # Safe delete d360 and move tasks to d180
        del_resp = self.client.post(
            reverse('operations-checklist:delete_phase', args=['d360']),
            {'task_action': 'move', 'target_phase_key': 'd180'},
        )
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(TimelinePhase.objects.filter(wedding=self.wedding, key='d360').exists())
        self.assertEqual(TaskMilestone.objects.filter(wedding=self.wedding, phase='d180').count(), 2)

    def test_start_from_zero_and_add_from_guide(self):
        TaskMilestone.objects.create(wedding=self.wedding, phase='d360', title='Old Task')
        resp = self.client.post(
            reverse('operations-checklist:reset_or_apply_preset'),
            {
                'mode': 'start_from_zero',
                'custom_phase_labels': ['Bulan 1: Lamaran & Budget', 'Bulan 2: Vendor & KUA'],
            },
        )
        self.assertEqual(resp.status_code, 302)
        phases = list(TimelinePhase.objects.filter(wedding=self.wedding).order_by('sort_order'))
        self.assertEqual(len(phases), 2)
        self.assertEqual(phases[0].label, 'Bulan 1: Lamaran & Budget')
        self.assertEqual(TaskMilestone.objects.filter(wedding=self.wedding).count(), 0)

        # Add a task from Smart Task Guide into the first custom phase via HTMX
        guide_resp = self.client.post(
            reverse('operations-checklist:add_guide_task'),
            {'topic_key': 'foundation', 'item_idx': '0', 'phase': phases[0].key},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(guide_resp.status_code, 200)
        self.assertEqual(TaskMilestone.objects.filter(wedding=self.wedding, phase=phases[0].key).count(), 1)
