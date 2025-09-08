from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='landing'),
    path('marketplace/', views.marketplace,name="marketplace"),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('seller/', views.seller, name='seller'),
    path('buyer/', views.buyer, name='buyer'),
    path('property/<int:listing_id>/', views.property_detail, name='property_detail'),
    path('mint-nft/<int:listing_id>/', views.mint_nft, name='mint_nft'),
    path('update-wallet-address/', views.update_wallet_address, name='update_wallet_address'),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path('save_listing_step/<int:step>/', views.save_listing_step, name='save_listing_step'),
    path('submit_listing/', views.submit_listing, name='submit_listing'),
    path('buy-nft/<int:listing_id>/', views.buy_nft, name='buy_nft'),
    path('buy-fractional/<int:listing_id>/', views.buy_fractional, name='buy_fractional'),
    
    # 🤖 Agent Integration URLs
    path('agent/validate/<int:listing_id>/', views.validate_listing_agent, name='validate_listing_agent'),
    path('agent/valuation/<int:listing_id>/', views.get_valuation_agent, name='get_valuation_agent'),
    path('agent/recommendations/', views.get_recommendations_agent, name='get_recommendations_agent'),
    path('agent/debug/<int:listing_id>/', views.debug_validation, name='debug_validation'),
    
    # 🔐 KYC Verification URLs
    path('kyc-verification/', views.kyc_verification, name='kyc_verification'),
    path('submit-kyc/', views.submit_kyc, name='submit_kyc'),
    path('check-kyc-status/', views.check_kyc_status, name='check_kyc_status'),
    path('sumsub-webhook/', views.sumsub_webhook, name='sumsub_webhook'),
]
