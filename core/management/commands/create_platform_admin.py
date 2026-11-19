"""
Management command to create or promote a Platform Admin account,
and optionally backfill AccountProfile for existing users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import AccountProfile, WeddingMembership


class Command(BaseCommand):
    help = 'Create or promote a Platform Admin account, or backfill AccountProfiles for existing users.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username for the Platform Admin account')
        parser.add_argument('--email', type=str, default='', help='Email for the Platform Admin account')
        parser.add_argument('--password', type=str, help='Password for the Platform Admin account')
        parser.add_argument(
            '--backfill',
            action='store_true',
            help='Backfill AccountProfile for all existing users without one.',
        )

    def handle(self, *args, **options):
        if options['backfill']:
            created_count = 0
            for user in User.objects.all():
                if not hasattr(user, 'profile'):
                    if user.is_superuser:
                        acc_type, quota = 'admin', 0
                    elif WeddingMembership.objects.filter(user=user, role='wo_manager').exists():
                        acc_type, quota = 'wo_manager', 5
                    elif WeddingMembership.objects.filter(user=user, role__in=('owner', 'co_owner')).exists():
                        acc_type, quota = 'couple', 1
                    elif WeddingMembership.objects.filter(user=user, role='crew').exists():
                        acc_type, quota = 'crew', 0
                    else:
                        acc_type, quota = 'couple', 1
                    AccountProfile.objects.create(
                        user=user,
                        account_type=acc_type,
                        project_quota=quota,
                    )
                    created_count += 1
            self.stdout.write(self.style.SUCCESS(f'Backfill selesai: {created_count} AccountProfile dibuat.'))

        username = options.get('username')
        if username:
            email = options.get('email') or f'{username}@rangkai.click'
            password = options.get('password')
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'is_staff': True, 'is_superuser': True},
            )
            if not created:
                user.is_staff = True
                user.is_superuser = True
                if email:
                    user.email = email
            if password:
                user.set_password(password)
            user.save()

            profile, _ = AccountProfile.objects.get_or_create(user=user)
            profile.account_type = 'admin'
            profile.project_quota = 0
            profile.plan_status = 'active'
            profile.save()

            action = 'dibuat' if created else 'diperbarui'
            self.stdout.write(self.style.SUCCESS(f'Platform Admin "{username}" berhasil {action} (ALL access).'))
