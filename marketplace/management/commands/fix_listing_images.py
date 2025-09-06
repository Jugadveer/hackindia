from django.core.management.base import BaseCommand
from marketplace.models import Listing, ListingImage

class Command(BaseCommand):
    help = 'Fix listing images by setting cover images from first uploaded image'

    def handle(self, *args, **options):
        listings = Listing.objects.filter(cover_image__isnull=True)
        
        if not listings.exists():
            self.stdout.write(self.style.SUCCESS('No listings need image fixes.'))
            return
        
        self.stdout.write(f'Found {listings.count()} listings without cover images.')
        
        fixed = 0
        for listing in listings:
            # Get the first image for this listing
            first_image = ListingImage.objects.filter(listing=listing).first()
            if first_image:
                listing.cover_image = first_image.image
                listing.save()
                fixed += 1
                self.stdout.write(f'Fixed cover image for listing: {listing.title}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {fixed} listing(s).')
        )
