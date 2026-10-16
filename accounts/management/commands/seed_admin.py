from django.core.management.base import BaseCommand

from accounts.models import User, UserRole


class Command(BaseCommand):
    help = 'Create a default SUPER_ADMIN user if missing'

    def add_arguments(self, parser):
        parser.add_argument('--email', default='admin@earthenergy.local')
        parser.add_argument('--mobile', default='9999999999')
        parser.add_argument('--password', required=True)
        parser.add_argument('--name', default='Super Admin')

    def handle(self, *args, **options):
        email = options['email']
        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(self.style.WARNING(f'Admin already exists: {email}'))
            return

        User.objects.create_superuser(
            email=email,
            mobile=options['mobile'],
            password=options['password'],
            full_name=options['name'],
            location='Hamirpur, UP',
            role=UserRole.SUPER_ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(f'Created SUPER_ADMIN {email}'))
