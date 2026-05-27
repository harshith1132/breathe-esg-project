from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Organization, UserProfile, DataSource


class Command(BaseCommand):
    help = 'Create initial superuser, org, and data sources'

    def handle(self, *args, **kwargs):
        # Create superuser
        if not User.objects.filter(username='admin').exists():
            user = User.objects.create_superuser(
                username='admin',
                email='harshith1132@gmail.com',
                password='Admin1234'
            )
            self.stdout.write('Superuser created')
        else:
            user = User.objects.get(username='admin')
            self.stdout.write('Superuser already exists')

        # Create organization
        org, _ = Organization.objects.get_or_create(
            slug='acme',
            defaults={'name': 'Acme Corp'}
        )
        self.stdout.write(f'Organization: {org.name}')

        # Create UserProfile
        from core.models import UserProfile
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'organization': org, 'role': 'admin'}
        )
        self.stdout.write('UserProfile created')

        # Create DataSources
        sources = [
            ('SAP Munich Plant', 'SAP'),
            ('Utility Portal', 'UTILITY'),
            ('Concur Travel', 'TRAVEL'),
        ]
        for name, source_type in sources:
            ds, created = DataSource.objects.get_or_create(
                organization=org,
                source_type=source_type,
                defaults={'name': name}
            )
            self.stdout.write(f'DataSource: {ds.name} ({"created" if created else "exists"})')

        self.stdout.write(self.style.SUCCESS('Setup complete'))