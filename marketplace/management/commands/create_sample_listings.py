from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from marketplace.models import Listing, Profile
import random
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create sample property listings for testing'

    def handle(self, *args, **options):
        # Create a test user if it doesn't exist
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            
            # Create profile
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    'kyc_verified': True,
                    'kyc_status': 'auto_approved'
                }
            )
            self.stdout.write(self.style.SUCCESS('Created test user'))
        
        # Sample properties data
        sample_properties = [
            {
                'title': 'Luxury Beachfront Villa',
                'city': 'Malibu',
                'state': 'CA',
                'property_type': 'residential',
                'bedrooms': 5,
                'bathrooms': 4,
                'size': Decimal('3500.00'),
                'year_built': 2020,
                'price': Decimal('2500000.00'),
                'valuation_min': Decimal('2400000.00'),
                'valuation_max': Decimal('2800000.00'),
                'status': 'available',
                'token_id': 'NFT-001',
                'validation_confidence': 0.95,
                'valuation_confidence': 0.88,
                'recommendation_score': 0.92
            },
            {
                'title': 'Modern City Apartment',
                'city': 'New York',
                'state': 'NY',
                'property_type': 'apartment',
                'bedrooms': 2,
                'bathrooms': 2,
                'size': Decimal('1200.00'),
                'year_built': 2018,
                'price': Decimal('1200000.00'),
                'valuation_min': Decimal('1150000.00'),
                'valuation_max': Decimal('1400000.00'),
                'status': 'available',
                'token_id': 'NFT-002',
                'validation_confidence': 0.89,
                'valuation_confidence': 0.85,
                'recommendation_score': 0.87
            },
            {
                'title': 'Rustic Mountain Cabin',
                'city': 'Aspen',
                'state': 'CO',
                'property_type': 'residential',
                'bedrooms': 3,
                'bathrooms': 2,
                'size': Decimal('1800.00'),
                'year_built': 2015,
                'price': Decimal('1800000.00'),
                'valuation_min': Decimal('1700000.00'),
                'valuation_max': Decimal('3100000.00'),
                'status': 'sold',
                'token_id': 'NFT-003',
                'validation_confidence': 0.92,
                'valuation_confidence': 0.90,
                'recommendation_score': 0.85
            },
            {
                'title': 'Downtown Office Space',
                'city': 'San Francisco',
                'state': 'CA',
                'property_type': 'commercial',
                'bedrooms': 0,
                'bathrooms': 3,
                'size': Decimal('5000.00'),
                'year_built': 2019,
                'price': Decimal('3500000.00'),
                'valuation_min': Decimal('3200000.00'),
                'valuation_max': Decimal('3800000.00'),
                'status': 'available',
                'token_id': 'NFT-004',
                'validation_confidence': 0.87,
                'valuation_confidence': 0.82,
                'recommendation_score': 0.78
            },
            {
                'title': 'Suburban Family Home',
                'city': 'Austin',
                'state': 'TX',
                'property_type': 'residential',
                'bedrooms': 4,
                'bathrooms': 3,
                'size': Decimal('2200.00'),
                'year_built': 2017,
                'price': Decimal('650000.00'),
                'valuation_min': Decimal('620000.00'),
                'valuation_max': Decimal('720000.00'),
                'status': 'pending_validation',
                'token_id': 'NFT-005',
                'validation_confidence': 0.75,
                'valuation_confidence': 0.80,
                'recommendation_score': 0.70
            },
            {
                'title': 'Luxury Penthouse',
                'city': 'Miami',
                'state': 'FL',
                'property_type': 'apartment',
                'bedrooms': 3,
                'bathrooms': 3,
                'size': Decimal('2800.00'),
                'year_built': 2021,
                'price': Decimal('1800000.00'),
                'valuation_min': Decimal('1750000.00'),
                'valuation_max': Decimal('1950000.00'),
                'status': 'available',
                'token_id': 'NFT-006',
                'validation_confidence': 0.94,
                'valuation_confidence': 0.91,
                'recommendation_score': 0.89
            }
        ]
        
        created_count = 0
        for prop_data in sample_properties:
            listing, created = Listing.objects.get_or_create(
                token_id=prop_data['token_id'],
                defaults={
                    'owner': user,
                    **prop_data
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} sample property listings')
        )
