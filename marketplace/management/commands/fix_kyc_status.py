from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from marketplace.models import Profile

class Command(BaseCommand):
    help = 'Fix KYC status for users'

    def handle(self, *args, **options):
        # Get all users
        users = User.objects.all()
        
        for user in users:
            try:
                profile = user.profile
                self.stdout.write(f"User {user.username}: kyc_verified={profile.kyc_verified}, kyc_status={profile.kyc_status}")
                
                # Fix the logic
                if profile.kyc_status in ['auto_approved', 'approved'] and not profile.kyc_verified:
                    profile.kyc_verified = True
                    profile.save()
                    self.stdout.write(f"Fixed {user.username}: Set kyc_verified=True")
                elif profile.kyc_verified and profile.kyc_status not in ['auto_approved', 'approved']:
                    profile.kyc_verified = False
                    profile.save()
                    self.stdout.write(f"Fixed {user.username}: Set kyc_verified=False")
                    
            except Profile.DoesNotExist:
                # Create profile if it doesn't exist
                profile = Profile.objects.create(user=user)
                self.stdout.write(f"Created profile for {user.username}")
        
        self.stdout.write(self.style.SUCCESS('KYC status fix completed'))
