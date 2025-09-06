from django.core.management.base import BaseCommand
from marketplace.models import Listing, Profile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix approved listings that need minting'

    def handle(self, *args, **options):
        # Find listings that are approved but not minted
        approved_unminted = Listing.objects.filter(
            status='available',
            validation_status='approved',
            token_id__isnull=True
        )
        
        self.stdout.write(f"Found {approved_unminted.count()} approved listings that need minting")
        
        for listing in approved_unminted:
            try:
                # Check if user has wallet address
                try:
                    profile = listing.owner.profile
                    if profile.wallet_address:
                        # Attempt to mint
                        from marketplace.utils.web3_client import web3_client
                        token_uri = f"ipfs://{listing.ipfs_metadata_cid}"
                        
                        mint_result = web3_client.mint_property(
                            to_address=profile.wallet_address,
                            token_uri=token_uri
                        )
                        
                        if mint_result['success']:
                            listing.token_id = str(mint_result['token_id'])
                            listing.contract_address = mint_result['contract_address']
                            listing.save()
                            self.stdout.write(
                                self.style.SUCCESS(f"Successfully minted NFT for listing {listing.id}")
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"Failed to mint NFT for listing {listing.id}: {mint_result.get('error')}")
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"User {listing.owner.username} has no wallet address for listing {listing.id}")
                        )
                except Profile.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"User {listing.owner.username} has no profile for listing {listing.id}")
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing listing {listing.id}: {e}")
                )
        
        self.stdout.write(self.style.SUCCESS('Finished processing approved listings'))
