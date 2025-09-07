from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    KYC_STATUS_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('pending', 'Pending Review'),
        ('auto_approved', 'Auto Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    wallet_address = models.CharField(max_length=100, blank=True, null=True)
    kyc_verified = models.BooleanField(default=False)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='not_submitted')
    kyc_submitted_at = models.DateTimeField(blank=True, null=True)
    kyc_reviewed_at = models.DateTimeField(blank=True, null=True)
    kyc_rejection_reason = models.TextField(blank=True, null=True)
    
    # Sumsub KYC fields
    sumsub_user_id = models.CharField(max_length=255, blank=True, null=True)
    sumsub_access_token = models.TextField(blank=True, null=True)
    sumsub_verification_status = models.CharField(max_length=50, blank=True, null=True)
    kyc_doc = models.FileField(upload_to='kyc_docs/', blank=True, null=True)

    def __str__(self):
        return self.user.username


class Listing(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending_validation', 'Pending Validation'),
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('rejected', 'Rejected'),
    ]

    PROPERTY_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('apartment', 'Apartment'),
        ('commercial', 'Commercial'),
        ('land', 'Land'),
        ('industrial', 'Industrial'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    # Basic property details
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPE_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='US')
    size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    bedrooms = models.IntegerField(blank=True, null=True)
    bathrooms = models.IntegerField(blank=True, null=True)
    year_built = models.PositiveIntegerField(blank=True, null=True)
    ownership_type = models.CharField(max_length=100, blank=True, null=True)

    # Media
    cover_image = models.ImageField(upload_to='listing_images/', blank=True, null=True)
    video = models.FileField(upload_to='listing_videos/', blank=True, null=True)

    # Compliance / docs
    title_deed = models.FileField(upload_to='listing_docs/', blank=True, null=True)
    tax_certificate = models.FileField(upload_to='listing_docs/', blank=True, null=True)
    utility_bills = models.FileField(upload_to='listing_docs/', blank=True, null=True)
    kyc_doc = models.FileField(upload_to='kyc_docs/', blank=True, null=True)

    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    valuation_min = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    valuation_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    fractionalisation = models.BooleanField(default=False)
    fraction_shares_total = models.PositiveIntegerField(default=1000)
    let_agent_suggest = models.BooleanField(default=False)

    # Blockchain & NFT
    token_id = models.CharField(max_length=100, blank=True, null=True)
    contract_address = models.CharField(max_length=100, blank=True, null=True)
    ipfs_metadata_cid = models.CharField(max_length=255, blank=True, null=True)
    
    # Agent Integration
    validation_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending')
    validation_confidence = models.FloatField(default=0.0)
    valuation_confidence = models.FloatField(default=0.0)
    recommendation_score = models.FloatField(default=0.0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or f"Listing #{self.id}"
    
    @property
    def display_price(self):
        """Get display price based on status"""
        if self.status == 'sold':
            return "Sold"
        elif self.status in ['pending_validation', 'submitted']:
            return "Price Hidden"
        elif self.price:
            return f"${self.price:,.0f}"
        elif self.let_agent_suggest and self.valuation_min:
            return f"${self.valuation_min:,.0f}"
        else:
            return "Price on Request"
    
    @property
    def display_valuation(self):
        """Get valuation range for display"""
        if self.valuation_min and self.valuation_max:
            return f"${self.valuation_min:,.0f} - ${self.valuation_max:,.0f}"
        elif self.valuation_min:
            return f"${self.valuation_min:,.0f}"
        else:
            return "Valuation Pending"
    
    @property
    def status_badge_color(self):
        """Get status badge color"""
        # Special case: approved but not minted
        if self.status == 'available' and not self.token_id:
            return 'blue'
        
        colors = {
            'available': 'green',
            'sold': 'red',
            'pending_validation': 'yellow',
            'rejected': 'red',
            'draft': 'gray',
            'submitted': 'yellow'  # Show as under review
        }
        return colors.get(self.status, 'gray')
    
    @property
    def status_badge_text(self):
        """Get status badge text"""
        # Special case: approved but not minted
        if self.status == 'available' and not self.token_id:
            return 'Needs Minting'
        
        texts = {
            'available': 'Available',
            'sold': 'Sold',
            'pending_validation': 'Under Review',
            'rejected': 'Rejected',
            'draft': 'Draft',
            'submitted': 'Under Review'  # Show as under review
        }
        return texts.get(self.status, 'Unknown')
    
    @property
    def full_location(self):
        """Get full location string"""
        parts = [self.city, self.state, self.country]
        return ', '.join(filter(None, parts))

    @property
    def fraction_shares_sold(self):
        try:
            total = sum(h.shares for h in self.fractionalholdings.all())
        except Exception:
            total = 0
        return total

    @property
    def fraction_shares_remaining(self):
        return max(0, (self.fraction_shares_total or 0) - self.fraction_shares_sold)


class ListingImage(models.Model):
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listing_images/')


class ListingDocument(models.Model):
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='listing_docs/')


class Transaction(models.Model):
    TOKEN_TYPE_CHOICES = [
        ('ERC721', 'Full NFT'),
        ('ERC1155', 'Fractional'),
    ]
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, related_name='transactions')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales')
    token_type = models.CharField(max_length=10, choices=TOKEN_TYPE_CHOICES)
    amount_paid = models.DecimalField(max_digits=18, decimal_places=2)
    transaction_hash = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class FractionalHolding(models.Model):
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, related_name='fractionalholdings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fractional_holdings')
    shares = models.PositiveIntegerField(default=0)
    amount_paid = models.DecimalField(max_digits=18, decimal_places=2)
    transaction_hash = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
