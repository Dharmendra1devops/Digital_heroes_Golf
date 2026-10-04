from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.charities.models import Charity, CharityEvent


DEMO_MARKER = 'DEMO ONLY:'
LEGACY_SAMPLE_EVENTS = (
    'DEMO ONLY: Community learning day',
    'DEMO ONLY: Neighborhood garden day',
)
DEMO_CAUSES = (
    {
        'slug': 'demo-community-learning-fund',
        'name': 'Community Learning',
        'legacy_name': 'DEMO ONLY: Community Learning Fund',
        'description': (
            'A cause area focused on access to learning resources and community education.'
        ),
        'is_featured': True,
        'display_order': 1,
    },
    {
        'slug': 'demo-green-spaces-project',
        'name': 'Green Spaces',
        'legacy_name': 'DEMO ONLY: Green Spaces Project',
        'description': (
            'A cause area focused on accessible green spaces and care for the local environment.'
        ),
        'is_featured': False,
        'display_order': 2,
    },
)


class Command(BaseCommand):
    help = 'Add the example cause categories used by the member workspace.'

    @transaction.atomic
    def handle(self, *args, **options):
        for item in DEMO_CAUSES:
            charity, created = Charity.objects.get_or_create(
                slug=item['slug'],
                defaults={
                    'name': item['name'],
                    'description': item['description'],
                    'is_active': True,
                    'is_featured': item['is_featured'],
                    'display_order': item['display_order'],
                },
            )
            if not created and charity.name not in (
                item['legacy_name'],
                f"{DEMO_MARKER} {item['name']}",
                item['name'],
            ):
                raise CommandError(
                    f"Refusing to overwrite existing cause '{charity.slug}'."
                )

            if created:
                self.stdout.write(f"Created {charity.name}")
            elif charity.name != item['name']:
                charity.name = item['name']
                charity.description = item['description']
                charity.is_active = True
                charity.is_featured = item['is_featured']
                charity.display_order = item['display_order']
                charity.save(
                    update_fields=(
                        'name',
                        'description',
                        'is_active',
                        'is_featured',
                        'display_order',
                        'updated_at',
                    )
                )
                self.stdout.write(f"Updated {charity.name}")
            else:
                self.stdout.write(f"Kept existing {charity.name}")

            CharityEvent.objects.filter(
                charity=charity,
                title__in=LEGACY_SAMPLE_EVENTS,
            ).delete()

        self.stdout.write(self.style.SUCCESS('Example cause categories are ready.'))
