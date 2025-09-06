from django.core.management.base import BaseCommand
from marketplace.models import Listing
import time

class Command(BaseCommand):
    help = 'Fix duplicate token IDs for listings'

    def handle(self, *args, **options):
        # Find listings with duplicate token IDs
        listings = Listing.objects.filter(token_id__isnull=False).order_by('id')
        
        seen_tokens = set()
        duplicates = []
        
        for listing in listings:
            if listing.token_id in seen_tokens:
                duplicates.append(listing)
            else:
                seen_tokens.add(listing.token_id)
        
        self.stdout.write(f"Found {len(duplicates)} listings with duplicate token IDs")
        
        # Fix duplicate token IDs
        for listing in duplicates:
            # Generate new unique token ID
            new_token_id = 1000 + hash(str(listing.id) + str(time.time())) % 10000
            old_token_id = listing.token_id
            listing.token_id = str(new_token_id)
            listing.save()
            
            self.stdout.write(
                self.style.SUCCESS(f"Fixed listing {listing.id}: {old_token_id} -> {new_token_id}")
            )
        
        self.stdout.write(self.style.SUCCESS('Finished fixing duplicate token IDs'))
