from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from .models import Profile, Listing, ListingImage, ListingDocument

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'wallet_address', 'kyc_status', 'kyc_verified', 'kyc_submitted_at')
    search_fields = ('user__username', 'phone', 'wallet_address')
    list_filter = ('kyc_status', 'kyc_verified')
    readonly_fields = ('kyc_submitted_at', 'kyc_reviewed_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone', 'wallet_address')
        }),
        ('KYC Status', {
            'fields': ('kyc_verified', 'kyc_status', 'kyc_submitted_at', 'kyc_reviewed_at', 'kyc_rejection_reason')
        }),
        ('KYC Document', {
            'fields': ('kyc_doc',)
        }),
        ('Sumsub Integration', {
            'fields': ('sumsub_user_id', 'sumsub_access_token', 'sumsub_verification_status'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_kyc', 'reject_kyc']
    
    def approve_kyc(self, request, queryset):
        """Approve selected KYC applications"""
        updated = 0
        for profile in queryset.filter(kyc_status='pending'):
            profile.kyc_verified = True
            profile.kyc_status = 'approved'
            profile.kyc_reviewed_at = timezone.now()
            profile.kyc_rejection_reason = None
            profile.save()
            updated += 1
        
        if updated:
            self.message_user(request, f"Successfully approved {updated} KYC application(s).", messages.SUCCESS)
        else:
            self.message_user(request, "No pending KYC applications selected.", messages.WARNING)
    
    approve_kyc.short_description = "Approve selected KYC applications"
    
    def reject_kyc(self, request, queryset):
        """Reject selected KYC applications"""
        updated = 0
        for profile in queryset.filter(kyc_status='pending'):
            profile.kyc_verified = False
            profile.kyc_status = 'rejected'
            profile.kyc_reviewed_at = timezone.now()
            profile.kyc_rejection_reason = "Rejected by admin review"
            profile.save()
            updated += 1
        
        if updated:
            self.message_user(request, f"Successfully rejected {updated} KYC application(s).", messages.SUCCESS)
        else:
            self.message_user(request, "No pending KYC applications selected.", messages.WARNING)
    
    reject_kyc.short_description = "Reject selected KYC applications"

class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'validation_status', 'price', 'city', 'created_at')
    list_filter = ('status', 'validation_status', 'property_type', 'created_at')
    search_fields = ('title', 'owner__username', 'city', 'state')
    readonly_fields = ('created_at', 'updated_at', 'ipfs_metadata_cid', 'token_id', 'contract_address')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'title', 'description', 'property_type', 'location', 'city', 'state', 'country')
        }),
        ('Property Details', {
            'fields': ('size', 'bedrooms', 'bathrooms', 'year_built', 'ownership_type')
        }),
        ('Pricing', {
            'fields': ('price', 'valuation_min', 'valuation_max', 'fractionalisation', 'let_agent_suggest')
        }),
        ('Media', {
            'fields': ('cover_image', 'video'),
            'classes': ('collapse',)
        }),
        ('Documents', {
            'fields': ('title_deed', 'tax_certificate', 'utility_bills', 'kyc_doc'),
            'classes': ('collapse',)
        }),
        ('Blockchain & IPFS', {
            'fields': ('token_id', 'contract_address', 'ipfs_metadata_cid'),
            'classes': ('collapse',)
        }),
        ('Agent Integration', {
            'fields': ('validation_status', 'validation_confidence', 'valuation_confidence', 'recommendation_score'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['approve_listings', 'reject_listings', 'mark_available']
    
    def approve_listings(self, request, queryset):
        """Approve selected listings"""
        updated = 0
        for listing in queryset.filter(status__in=['submitted', 'pending_validation']):
            listing.status = 'available'
            listing.validation_status = 'approved'
            listing.validation_confidence = 0.9  # High confidence for admin approval
            listing.save()
            updated += 1
        
        if updated:
            self.message_user(request, f"Successfully approved {updated} listing(s).", messages.SUCCESS)
        else:
            self.message_user(request, "No pending listings selected.", messages.WARNING)
    
    approve_listings.short_description = "Approve selected listings"
    
    def reject_listings(self, request, queryset):
        """Reject selected listings"""
        updated = 0
        for listing in queryset.filter(status__in=['submitted', 'pending_validation']):
            listing.status = 'rejected'
            listing.validation_status = 'rejected'
            listing.validation_confidence = 0.1  # Low confidence for rejection
            listing.save()
            updated += 1
        
        if updated:
            self.message_user(request, f"Successfully rejected {updated} listing(s).", messages.SUCCESS)
        else:
            self.message_user(request, "No pending listings selected.", messages.WARNING)
    
    reject_listings.short_description = "Reject selected listings"
    
    def mark_available(self, request, queryset):
        """Mark selected listings as available"""
        updated = 0
        for listing in queryset:
            listing.status = 'available'
            if listing.validation_status != 'approved':
                listing.validation_status = 'approved'
                listing.validation_confidence = 0.8
            listing.save()
            updated += 1
        
        if updated:
            self.message_user(request, f"Successfully marked {updated} listing(s) as available.", messages.SUCCESS)
        else:
            self.message_user(request, "No listings selected.", messages.WARNING)
    
    mark_available.short_description = "Mark as available"

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Listing, ListingAdmin)
admin.site.register(ListingImage)
admin.site.register(ListingDocument)