import logging
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import requests, hashlib, hmac
from django.http import JsonResponse
import threading
from django.conf import settings
from django.utils import timezone
from django.db import models
from .models import Listing, Profile, Transaction, FractionalHolding
from .utils.ipfs import handle_property_upload
from .utils.sumsub_client import sumsub_client

# Configure logging
logger = logging.getLogger(__name__)

SUMSUB_SECRET_KEY = "your_secret_key"
SUMSUB_APP_TOKEN = "your_app_token"
SUMSUB_BASE_URL = "https://api.sumsub.com"


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("marketplace")  # go to marketplace/dashboard
        else:
            messages.error(request, "Invalid username or password")
            return redirect("landing")
    return redirect("landing")  # fallback

def logout_view(request):
    logout(request)
    return redirect("landing")

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        phone = request.POST.get("phone")
        wallet = request.POST.get("wallet_address")

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("landing")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("landing")

        user = User.objects.create_user(username=username, email=email, password=password1)

        # ✅ Create profile manually
        Profile.objects.create(user=user, phone=phone, wallet_address=wallet)

        login(request, user)
        messages.success(request, "Account created successfully")
        return redirect("marketplace")
    
    return redirect("landing")


from .models import ListingImage, ListingDocument


def save_listing_step(request, step):
    listing_id = request.POST.get("listing_id")
    listing = None

    if listing_id:
        listing = get_object_or_404(Listing, id=listing_id, owner=request.user)

    # Step 1: Media (images, video)
    if step == 1:
        if not listing:
            listing = Listing.objects.create(owner=request.user, status="draft")

        images = request.FILES.getlist("images")
        if images:
            for idx, img in enumerate(images):
                # First image → also cover image
                if idx == 0:
                    listing.cover_image = img
                    listing.save()

                # Save ALL images in ListingImage (including the first one)
                ListingImage.objects.create(listing=listing, image=img)

        video = request.FILES.get("video")
        if video:
            listing.video = video
            listing.save()

    # Step 2: Property Details
    elif step == 2:
        if listing:
            listing.title = request.POST.get("title")
            listing.description = request.POST.get("description")
            listing.location = request.POST.get("location")
            listing.city=request.POST.get("city"),
            listing.state=request.POST.get("state"),
            listing.country=request.POST.get("country"),
            listing.property_type = request.POST.get("property_type")
            listing.size = request.POST.get("size") or None
            listing.bedrooms = request.POST.get("bedrooms") or None
            listing.bathrooms = request.POST.get("bathrooms") or None
            listing.year_built = request.POST.get("year_built") or None
            listing.ownership_type = request.POST.get("ownership_type")
            listing.save()

    # Step 3: Compliance
    elif step == 3 and listing:
        if request.FILES.get("title_deed"):
            listing.title_deed = request.FILES["title_deed"]
        if request.FILES.get("tax_certificate"):
            listing.tax_certificate = request.FILES["tax_certificate"]
        if request.FILES.get("utility_bills"):
            listing.utility_bills = request.FILES["utility_bills"]
        if request.FILES.get("kyc_doc"):
            listing.kyc_doc = request.FILES["kyc_doc"]
        listing.save()

    # Step 4: Pricing
    elif step == 4 and listing:
        listing.price = request.POST.get("price") or None
        listing.fractionalisation = request.POST.get("fractionalisation") == "true"
        listing.let_agent_suggest = request.POST.get("let_agent_suggest") == "true"
        listing.save()

    # # Step 5: Preview - nothing to save, just confirmation
    elif step == 5:
        pass

    return JsonResponse({"success": True, "listing_id": listing.id if listing else None})




def submit_listing(request):
    if request.method == 'POST':
        listing_id = request.POST.get('listing_id')
        if not listing_id:
            return JsonResponse({'success': False, 'error': 'Missing listing ID'})

        listing = get_object_or_404(Listing, id=listing_id, owner=request.user)

        try:
            # 🤖 Validate listing using Asset Validation Agent (if enabled)
            validation_result = None
            if settings.AGENT_SETTINGS.get('VALIDATION_ENABLED', True) and not settings.AGENT_SETTINGS.get('BYPASS_VALIDATION', False):
                from agents.clients import agent_client
                validation_result = agent_client.validate_listing(listing, request.user)
                
                if validation_result.get('status') != 'APPROVED':
                    # Get validation reasons for better error message
                    reasons = validation_result.get('reasons', ['Unknown validation error'])
                    error_message = f"Listing validation failed: {', '.join(reasons)}"
                    
                    return JsonResponse({
                        'success': False, 
                        'error': error_message,
                        'validation_errors': reasons,
                        'validation_result': validation_result
                    })
            else:
                # Bypass validation for testing
                validation_result = {
                    'status': 'APPROVED',
                    'reasons': ['Validation bypassed for testing'],
                    'listing_id': listing.id,
                    'user_id': request.user.id
                }

            # 🔗 Upload files + metadata to IPFS
            metadata_cid = handle_property_upload(request.FILES, request.POST)

            # Save CID and set listing to under review; do NOT auto-approve synchronously
            listing.ipfs_metadata_cid = metadata_cid.replace('ipfs://', '')  # Store just the CID, not the full URI
            listing.status = 'submitted'
            listing.validation_status = 'pending'
            listing.save()

            # Kick off background validation + optional auto-minting
            def _background_validate_and_maybe_mint(listing_id: int, user_id: int):
                try:
                    lst = Listing.objects.get(id=listing_id)
                    usr = User.objects.get(id=user_id)
                    if settings.AGENT_SETTINGS.get('VALIDATION_ENABLED', True) and not settings.AGENT_SETTINGS.get('BYPASS_VALIDATION', False):
                        from agents.clients import agent_client
                        validation_result = agent_client.validate_listing(lst, usr)
                        if validation_result.get('status') == 'APPROVED':
                            lst.status = 'available'
                            lst.validation_status = 'approved'
                            lst.validation_confidence = validation_result.get('confidence', 0.8)
                            # Auto-mint if wallet available
                            try:
                                profile = usr.profile
                                if profile.wallet_address and lst.ipfs_metadata_cid:
                                    from .utils.web3_client import web3_client
                                    token_uri = f"ipfs://{lst.ipfs_metadata_cid}"
                                    mint_result = web3_client.mint_property(
                                        to_address=profile.wallet_address,
                                        token_uri=token_uri
                                    )
                                    if mint_result.get('success'):
                                        lst.token_id = str(mint_result.get('token_id'))
                                        lst.contract_address = mint_result.get('contract_address')
                            except Exception as e:
                                logger.error(f"Background auto-minting error for listing {lst.id}: {e}")
                            lst.save()
                        else:
                            lst.validation_status = 'rejected'
                            lst.status = 'rejected'
                            lst.save()
                except Exception as e:
                    logger.error(f"Background validation error: {e}")

            threading.Thread(target=_background_validate_and_maybe_mint, args=(listing.id, request.user.id), daemon=True).start()

            # Respond immediately with under-review status for better UX
            return JsonResponse({
                'success': True,
                'metadata_cid': metadata_cid,
                'status': 'submitted',
                'message': 'Your property is under review.'
            })
        except Exception as e:
            logger.error(f"Error submitting listing: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})



def upload_listing_to_ipfs(request):
    if request.method == "POST":
        try:
            metadata_cid = handle_property_upload(request.FILES, request.POST)
            return JsonResponse({"success": True, "metadata_cid": metadata_cid})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request"})



# def home(request):
#     return render(request, 'landing.html')


def home(request):
    if request.user.is_authenticated:
        return redirect('marketplace')  # use your marketplace URL name here
    return render(request, 'landing.html')


def dashboard(request):
    """User dashboard showing their listings"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Debug: Check user authentication
    logger.info(f"Dashboard request - User: {request.user}, Authenticated: {request.user.is_authenticated}, Username: {request.user.username}")
    
    # Debug: Check if user123 exists and has listings
    from django.contrib.auth.models import User
    user123 = User.objects.filter(username='user123').first()
    if user123:
        user123_listings = Listing.objects.filter(owner=user123)
        logger.info(f"Direct check - user123 exists, has {user123_listings.count()} listings")
        for listing in user123_listings:
            logger.info(f"  - Listing {listing.id}: {listing.title}, Status: {listing.status}")
    else:
        logger.info("Direct check - user123 does not exist")
    
    # Get user's listings
    user_listings = Listing.objects.filter(owner=request.user).order_by('-created_at')
    
    # Debug: Check all listings for this user
    all_user_listings = Listing.objects.filter(owner=request.user)
    logger.info(f"All listings for user {request.user.username}: {all_user_listings.count()}")
    for listing in all_user_listings:
        logger.info(f"  - Listing {listing.id}: {listing.title}, Status: {listing.status}, Validation: {listing.validation_status}, Token: {listing.token_id}")
    
    # Get user profile
    try:
        profile = request.user.profile
        kyc_verified = profile.kyc_verified or profile.kyc_status in ['auto_approved', 'approved']
        kyc_status = profile.kyc_status
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = Profile.objects.create(user=request.user)
        kyc_verified = False
        kyc_status = 'not_submitted'
    
    # Debug logging
    logger.info(f"Dashboard for user {request.user.username}: {user_listings.count()} listings, KYC: {kyc_verified}, Status: {kyc_status}")
    for listing in user_listings:
        logger.info(f"  - Listing {listing.id}: {listing.title}, Status: {listing.status}, Token ID: {listing.token_id}")
    
    context = {
        'listings': user_listings,
        'kyc_verified': kyc_verified,
        'kyc_status': kyc_status,
        'debug_info': f"User: {request.user.username}, Listings: {user_listings.count()}"
    }
    return render(request, 'dashboard.html', context)


def property_detail(request, listing_id):
    """Detailed property view with full information"""
    try:
        listing = Listing.objects.get(id=listing_id)
    except Listing.DoesNotExist:
        return render(request, '404.html', {'message': 'Property not found'})
    
    # Get user profile for KYC status
    kyc_verified = False
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            kyc_verified = profile.kyc_verified or profile.kyc_status in ['auto_approved', 'approved']
        except Profile.DoesNotExist:
            pass
    
    # Get all images for this listing
    listing_images = ListingImage.objects.filter(listing=listing)
    
    # Get all documents for this listing
    listing_documents = ListingDocument.objects.filter(listing=listing)
    
    # Get similar properties (recommendations)
    similar_listings = []
    if kyc_verified and request.user.is_authenticated:
        try:
            from agents.clients import agent_client
            recommendation_result = agent_client.get_recommendations(request.user, limit=5)
            recommended_listing_ids = recommendation_result.get('recommendations', [])
            similar_listings = Listing.objects.filter(
                id__in=recommended_listing_ids,
                status='available'
            ).exclude(id=listing_id)[:4]
        except Exception as e:
            logger.error(f"Failed to get similar properties: {e}")
    
    context = {
        'listing': listing,
        'listing_images': listing_images,
        'listing_documents': listing_documents,
        'similar_listings': similar_listings,
        'kyc_verified': kyc_verified,
        'is_owner': request.user == listing.owner if request.user.is_authenticated else False
    }
    return render(request, 'property_detail.html', context)


def update_wallet_address(request):
    """Update user's wallet address"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            wallet_address = data.get('wallet_address')
            
            if not wallet_address:
                return JsonResponse({'success': False, 'error': 'Wallet address is required'})
            
            # Get or create user profile
            try:
                profile = request.user.profile
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=request.user)
            
            # Update wallet address
            profile.wallet_address = wallet_address
            profile.save()
            
            logger.info(f"Updated wallet address for user {request.user.username}: {wallet_address}")
            
            return JsonResponse({
                'success': True,
                'wallet_address': wallet_address
            })
            
        except Exception as e:
            logger.error(f"Failed to update wallet address: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def mint_nft(request, listing_id):
    """Mint NFT for an approved listing"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        listing = Listing.objects.get(id=listing_id, owner=request.user)
    except Listing.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Listing not found'})
    
    # Check if listing is approved for minting
    if listing.status != 'available' or listing.validation_status != 'approved':
        return JsonResponse({
            'success': False, 
            'error': 'Listing must be approved before minting NFT'
        })
    
    # Check if already minted
    if listing.token_id and listing.contract_address:
        return JsonResponse({
            'success': False, 
            'error': 'NFT already minted for this listing'
        })
    
    # Get user's wallet address
    try:
        profile = request.user.profile
        wallet_address = profile.wallet_address
        if not wallet_address:
            return JsonResponse({
                'success': False, 
                'error': 'Wallet address not set. Please update your profile.'
            })
    except Profile.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Profile not found. Please complete KYC verification.'
        })
    
    # Prepare token URI (IPFS metadata)
    if not listing.ipfs_metadata_cid:
        return JsonResponse({
            'success': False, 
            'error': 'Property metadata not uploaded to IPFS'
        })
    
    token_uri = f"ipfs://{listing.ipfs_metadata_cid}"
    
    # Mint the NFT
    try:
        from .utils.web3_client import web3_client
        
        result = web3_client.mint_property(
            to_address=wallet_address,
            token_uri=token_uri
        )
        
        if result['success']:
            # Update listing with NFT information
            listing.token_id = str(result['token_id'])
            listing.contract_address = result['contract_address']
            listing.status = 'available'  # Ensure it's available
            listing.save()
            
            logger.info(f"Successfully minted NFT for listing {listing_id}: {result}")
            
            return JsonResponse({
                'success': True,
                'token_id': result['token_id'],
                'transaction_hash': result['transaction_hash'],
                'contract_address': result['contract_address'],
                'message': 'NFT minted successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to mint NFT')
            })
            
    except Exception as e:
        logger.error(f"Failed to mint NFT for listing {listing_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Failed to mint NFT: {str(e)}'
        })


def marketplace(request):
    # 🤖 Get listings with agent integration
    listings = []
    recommendations = []
    kyc_verified = False
    kyc_status = 'not_submitted'
    kyc_status_message = ''
    
    if request.user.is_authenticated:
        # Check KYC status
        try:
            profile = request.user.profile
            kyc_verified = profile.kyc_verified or profile.kyc_status in ['auto_approved', 'approved']
            kyc_status = profile.kyc_status
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = Profile.objects.create(user=request.user)
            kyc_verified = False
            kyc_status = 'not_submitted'
    
    # Get all listings for the marketplace (both public and user's own)
    # Public marketplace shows only minted/sold listings
    # "My Listings" filter will show all user's listings regardless of status
    all_listings = Listing.objects.filter(
        status__in=['submitted', 'available', 'sold', 'rejected'],
        validation_status__in=['pending', 'approved', 'rejected']
    ).order_by('-created_at')
    
    # For public display, filter to only show minted/sold listings
    public_listings = all_listings.filter(
        models.Q(token_id__isnull=False) | models.Q(status='sold')
    )
    
    # Use all_listings for the template so "My Listings" filter can work
    listings = all_listings
    
    # Apply agent recommendations if user is KYC verified
    if kyc_verified and request.user.is_authenticated:
        try:
            from agents.clients import agent_client
            recommendation_result = agent_client.get_recommendations(request.user, limit=10)
            recommended_listing_ids = recommendation_result.get('recommendations', [])
            
            # Reorder listings based on recommendations
            if recommended_listing_ids:
                # Create a mapping of listing IDs to their recommendation scores
                recommendation_map = {lid: idx for idx, lid in enumerate(recommended_listing_ids)}
                
                # Sort listings by recommendation score (lower index = higher priority)
                listings = sorted(listings, key=lambda x: recommendation_map.get(x.id, 999))
                
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
    
    # Apply agent valuations to listings (map service -> model fields)
    for listing in listings:
        if listing.status == 'available' and not listing.valuation_min:
            try:
                from agents.clients import agent_client
                valuation_result = agent_client.calculate_valuation(listing)
                # Support both interface success wrapper and direct payloads
                if valuation_result:
                    valuation_range = valuation_result.get('valuation_range') or {}
                    min_val = valuation_range.get('min')
                    max_val = valuation_range.get('max')
                    confidence = valuation_result.get('confidence_score', 0.0)
                    if min_val and max_val:
                        listing.valuation_min = min_val
                        listing.valuation_max = max_val
                        listing.valuation_confidence = confidence
                        listing.save()
            except Exception as e:
                logger.error(f"Failed to get valuation for listing {listing.id}: {e}")
    
    context = {
        'listings': listings,
        'recommendations': recommendations,
        'kyc_verified': kyc_verified,
        'kyc_status': kyc_status
    }
    return render(request, 'marketplace.html', context)


# 🤖 Agent Integration Views

def validate_listing_agent(request, listing_id):
    """API endpoint to validate listing using Asset Validation Agent"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        listing = get_object_or_404(Listing, id=listing_id, owner=request.user)
        from agents.clients import agent_client
        
        validation_result = agent_client.validate_listing(listing, request.user)
        
        return JsonResponse({
            'success': True,
            'validation_result': validation_result
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def get_valuation_agent(request, listing_id):
    """API endpoint to get property valuation using Valuation Agent"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        listing = get_object_or_404(Listing, id=listing_id, owner=request.user)
        from agents.clients import agent_client
        
        valuation_result = agent_client.calculate_valuation(listing)
        
        return JsonResponse({
            'success': True,
            'valuation_result': valuation_result
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def get_recommendations_agent(request):
    """API endpoint to get property recommendations using Recommendation Agent"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        limit = int(request.GET.get('limit', 5))
        from agents.clients import agent_client
        
        recommendation_result = agent_client.get_recommendations(request.user, limit)
        
        return JsonResponse({
            'success': True,
            'recommendation_result': recommendation_result
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# 🔐 KYC Verification System

def kyc_verification(request):
    """KYC verification page for users who haven't completed verification"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Check if user already has KYC verified
    try:
        profile = request.user.profile
        if profile.kyc_verified:
            messages.info(request, "Your KYC is already verified!")
            return redirect('marketplace')
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        Profile.objects.create(user=request.user)
    
    context = {
        'user': request.user,
        'kyc_verified': False
    }
    return render(request, 'kyc_verification.html', context)


def submit_kyc(request):
    """Handle KYC document submission using Sumsub"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    if request.method == 'POST':
        try:
            # Get or create user profile
            try:
                profile = request.user.profile
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=request.user)
            
            # Handle KYC document upload
            if 'kyc_document' in request.FILES:
                kyc_doc = request.FILES['kyc_document']
                
                # 🤖 Smart Auto-Approval System
                from marketplace.utils.kyc_validator import kyc_validator
                
                # Validate document for auto-approval
                validation_result = kyc_validator.validate_document(kyc_doc)
                
                # Save the document locally
                profile.kyc_doc = kyc_doc
                profile.kyc_submitted_at = timezone.now()
                
                if validation_result['auto_approve']:
                    # Auto-approve KYC
                    profile.kyc_verified = True
                    profile.kyc_status = 'auto_approved'
                    profile.save()
                    
                    logger.info(f"KYC auto-approved for user {request.user.id} with confidence {validation_result['confidence_score']:.2f}")
                    
                    messages.success(request, "KYC verification completed automatically! You can now create listings.")
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'KYC verification completed automatically! You can now create listings.',
                        'auto_approved': True,
                        'confidence_score': validation_result['confidence_score'],
                        'redirect_url': '/marketplace/'
                    })
                else:
                    # Fallback to Sumsub or manual review
                    profile.kyc_verified = False
                    profile.kyc_status = 'pending'
                    profile.save()
                    
                    # Try Sumsub first
                    try:
                        from marketplace.utils.sumsub_client import sumsub_client
                        
                        # Prepare user data for Sumsub
                        user_data = {
                            'first_name': request.user.first_name or 'User',
                            'last_name': request.user.last_name or 'Name',
                            'email': request.user.email or '',
                            'phone': '',  # Add phone field if you have it
                            'country': 'US',  # Default country, you can make this configurable
                            'dob': '',  # Add date of birth if you have it
                        }
                        
                        # Create unique user ID for Sumsub
                        sumsub_user_id = f"user_{request.user.id}_{int(time.time())}"
                        
                        # Initiate verification process
                        verification_result = sumsub_client.initiate_verification(sumsub_user_id, user_data)
                        
                        if verification_result['success']:
                            # Store Sumsub data in profile
                            profile.sumsub_user_id = sumsub_user_id
                            profile.sumsub_access_token = verification_result.get('access_token')
                            profile.save()
                            
                            messages.success(request, "KYC verification initiated! Please complete the verification process.")
                            
                            return JsonResponse({
                                'success': True,
                                'message': 'KYC verification initiated successfully! Please complete the verification process.',
                                'verification_url': verification_result.get('verification_url'),
                                'redirect_url': '/marketplace/'
                            })
                    except Exception as e:
                        logger.error(f"Sumsub verification failed: {e}")
                    
                    # Manual review fallback
                    messages.success(request, "KYC verification submitted for manual review!")
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'KYC verification submitted for manual review! You will be notified once reviewed.',
                        'validation_reasons': validation_result['reasons'],
                        'redirect_url': '/marketplace/'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Please upload a KYC document'
                })
                
        except Exception as e:
            logger.error(f"KYC submission error: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Error submitting KYC: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
def buy_nft(request, listing_id):
    """Buy full NFT: KYC + wallet checks, mint/transfer, log tx"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    try:
        profile = request.user.profile
        if not (profile.kyc_verified or profile.kyc_status in ['auto_approved', 'approved']):
            return JsonResponse({'success': False, 'require_kyc': True, 'error': 'KYC required'})
        if not profile.wallet_address:
            return JsonResponse({'success': False, 'require_wallet': True, 'error': 'Wallet not connected'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'require_kyc': True, 'error': 'KYC required'})

    try:
        listing = Listing.objects.get(id=listing_id)
        seller = listing.owner
        token_uri = f"ipfs://{listing.ipfs_metadata_cid}" if listing.ipfs_metadata_cid else None

        from .utils.web3_client import web3_client
        # If not minted, mint to seller first; then transfer (mocked as a single call here)
        result = web3_client.mint_property(
            to_address=profile.wallet_address,
            token_uri=token_uri or 'ipfs://'
        )
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': result.get('error', 'Blockchain transaction failed')})

        # Update listing
        listing.token_id = str(result.get('token_id'))
        listing.contract_address = result.get('contract_address')
        listing.status = 'sold'
        listing.save()

        # Log transaction
        Transaction.objects.create(
            listing=listing,
            buyer=request.user,
            seller=seller,
            token_type='ERC721',
            amount_paid=listing.price or 0,
            transaction_hash=result.get('transaction_hash')
        )

        return JsonResponse({
            'success': True,
            'message': 'Congratulations! You now own this property NFT.',
            'transaction_hash': result.get('transaction_hash'),
            'token_id': result.get('token_id'),
        })
    except Exception as e:
        logger.error(f"Buy NFT failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


def buy_fractional(request, listing_id):
    """Buy fractional shares (mock ERC1155). Expects JSON {shares} """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    try:
        profile = request.user.profile
        if not (profile.kyc_verified or profile.kyc_status in ['auto_approved', 'approved']):
            return JsonResponse({'success': False, 'require_kyc': True, 'error': 'KYC required'})
        if not profile.wallet_address:
            return JsonResponse({'success': False, 'require_wallet': True, 'error': 'Wallet not connected'})
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'require_kyc': True, 'error': 'KYC required'})

    try:
        import json
        data = json.loads(request.body or '{}')
        shares = int(data.get('shares', 0))
        if shares <= 0:
            return JsonResponse({'success': False, 'error': 'Invalid share quantity'})

        listing = Listing.objects.get(id=listing_id)
        if not listing.fractionalisation:
            return JsonResponse({'success': False, 'error': 'Fractionalization not enabled for this listing'})

        remaining = listing.fraction_shares_remaining
        if shares > remaining:
            return JsonResponse({'success': False, 'error': f'Only {remaining} shares remaining'})

        # Price per share (simple: listing.price / total)
        total_price = 0
        try:
            if listing.price and listing.fraction_shares_total:
                total_price = float(listing.price) * shares / float(listing.fraction_shares_total)
        except Exception:
            total_price = 0

        from .utils.web3_client import web3_client
        # Mock fractional transfer using same mint call to keep demo simple
        result = web3_client.mint_property(
            to_address=profile.wallet_address,
            token_uri=f"ipfs://{listing.ipfs_metadata_cid}#fractional"
        )
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': result.get('error', 'Blockchain transaction failed')})

        FractionalHolding.objects.create(
            listing=listing,
            user=request.user,
            shares=shares,
            amount_paid=total_price,
            transaction_hash=result.get('transaction_hash')
        )

        return JsonResponse({
            'success': True,
            'message': f'Purchased {shares} shares successfully.',
            'transaction_hash': result.get('transaction_hash'),
            'shares': shares,
            'remaining': listing.fraction_shares_remaining
        })
    except Exception as e:
        logger.error(f"Buy fractional failed: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


def check_kyc_status(request):
    """Check user's KYC verification status"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        profile = request.user.profile
        return JsonResponse({
            'success': True,
            'kyc_verified': profile.kyc_verified,
            'kyc_status': profile.kyc_status,
            'has_kyc_doc': bool(profile.kyc_doc),
            'kyc_submitted_at': profile.kyc_submitted_at.isoformat() if profile.kyc_submitted_at else None,
            'kyc_rejection_reason': profile.kyc_rejection_reason
        })
    except Profile.DoesNotExist:
        return JsonResponse({
            'success': True,
            'kyc_verified': False,
            'kyc_status': 'not_submitted',
            'has_kyc_doc': False,
            'kyc_submitted_at': None,
            'kyc_rejection_reason': None
        })


def debug_validation(request, listing_id):
    """Debug endpoint to see validation details"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        listing = get_object_or_404(Listing, id=listing_id, owner=request.user)
        from agents.clients import agent_client
        
        # Get validation result
        validation_result = agent_client.validate_listing(listing, request.user)
        
        # Get listing details for debugging
        listing_details = {
            'id': listing.id,
            'title': listing.title,
            'description': listing.description,
            'location': listing.location,
            'property_type': listing.property_type,
            'size': float(listing.size) if listing.size else None,
            'bedrooms': listing.bedrooms,
            'year_built': listing.year_built,
            'has_title_deed': bool(listing.title_deed),
            'has_tax_certificate': bool(listing.tax_certificate),
            'has_utility_bills': bool(listing.utility_bills),
            'has_kyc_doc': bool(listing.kyc_doc),
            'status': listing.status
        }
        
        # Get user details for debugging
        try:
            profile = request.user.profile
            user_details = {
                'id': request.user.id,
                'username': request.user.username,
                'kyc_verified': profile.kyc_verified,
                'has_profile': True
            }
        except:
            user_details = {
                'id': request.user.id,
                'username': request.user.username,
                'kyc_verified': False,
                'has_profile': False
            }
        
        return JsonResponse({
            'success': True,
            'validation_result': validation_result,
            'listing_details': listing_details,
            'user_details': user_details
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def sumsub_webhook(request):
    """Handle Sumsub webhook for verification status updates"""
    if request.method == 'POST':
        try:
            import json
            webhook_data = json.loads(request.body)
            
            # Extract user ID from webhook data
            user_id = webhook_data.get('applicantId', '')
            verification_status = webhook_data.get('reviewResult', {}).get('reviewAnswer', 'UNKNOWN')
            
            # Find user by Sumsub user ID
            try:
                profile = Profile.objects.get(sumsub_user_id=user_id)
                
                # Update verification status
                profile.sumsub_verification_status = verification_status
                
                # Set KYC verified based on status
                if verification_status == 'GREEN':
                    profile.kyc_verified = True
                else:
                    profile.kyc_verified = False
                
                profile.save()
                
                logger.info(f"Updated KYC status for user {profile.user.username}: {verification_status}")
                
                return JsonResponse({'success': True, 'message': 'Webhook processed successfully'})
                
            except Profile.DoesNotExist:
                logger.error(f"Profile not found for Sumsub user ID: {user_id}")
                return JsonResponse({'success': False, 'error': 'Profile not found'})
                
        except Exception as e:
            logger.error(f"Sumsub webhook error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


