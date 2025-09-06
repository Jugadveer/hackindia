from .models import Profile

def kyc_status(request):
    """Add KYC status to all templates"""
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            kyc_verified = profile.kyc_verified or profile.kyc_status in ['auto_approved', 'approved']
            kyc_status = profile.kyc_status
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = Profile.objects.create(user=request.user)
            kyc_verified = False
            kyc_status = 'not_submitted'
        
        return {
            'kyc_verified': kyc_verified,
            'kyc_status': kyc_status,
            'user_profile': profile
        }
    return {
        'kyc_verified': False,
        'kyc_status': 'not_submitted',
        'user_profile': None
    }
