from django.core.management.base import BaseCommand
from marketplace.models import Listing

class Command(BaseCommand):
    help = 'Approve all pending listings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be approved without making changes',
        )

    def handle(self, *args, **options):
        # Get all pending listings
        pending_listings = Listing.objects.filter(
            status__in=['submitted', 'pending_validation']
        )
        
        if not pending_listings.exists():
            self.stdout.write(self.style.WARNING('No pending listings found.'))
            return
        
        self.stdout.write(f'Found {pending_listings.count()} pending listings:')
        
        for listing in pending_listings:
            self.stdout.write(f'  - {listing.title} (ID: {listing.id}) by {listing.owner.username}')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry run mode - no changes made.'))
            return
        
        # Approve all pending listings
        updated = 0
        for listing in pending_listings:
            listing.status = 'available'
            listing.validation_status = 'approved'
            listing.validation_confidence = 0.8
            listing.save()
            updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully approved {updated} listing(s).')
        )
