"""
Django Integration - API Clients for MeTTa Agents
Purpose: Integrate MeTTa agents with Django views and models
"""

import json
import logging
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.contrib.auth.models import User
from marketplace.models import Listing, Profile

# Configure logging
logger = logging.getLogger(__name__)

try:
    from .services.validation_service import validation_service
    from .services.valuation_service import valuation_service
    from .services.recommendation_service import recommendation_service
    AGENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"MeTTa agents not available: {e}")
    AGENTS_AVAILABLE = False
    validation_service = None
    valuation_service = None
    recommendation_service = None

class AgentClient:
    """Base client for interacting with MeTTa agents"""
    
    def __init__(self):
        self.validation_service = validation_service
        self.valuation_service = valuation_service
        self.recommendation_service = recommendation_service
    
    def validate_listing(self, listing: Listing, user: User) -> Dict[str, Any]:
        """
        Validate a property listing using the Asset Validation Agent
        
        Args:
            listing: Django Listing model instance
            user: Django User model instance
            
        Returns:
            Validation result dictionary
        """
        if not AGENTS_AVAILABLE:
            # Fallback validation without MeTTa agents
            return self._fallback_validation(listing, user)
        
        try:
            # Prepare listing data
            listing_data = {
                "id": listing.id,
                "title": listing.title,
                "description": listing.description,
                "location": listing.location,
                "property_type": listing.property_type,
                "size": float(listing.size) if listing.size else 0,
                "bedrooms": listing.bedrooms,
                "year_built": listing.year_built,
                "ownership_type": listing.ownership_type,
                "price": float(listing.price) if listing.price else 0,
                "documents": {
                    "title_deed": bool(listing.title_deed),
                    "tax_certificate": bool(listing.tax_certificate),
                    "utility_bills": bool(listing.utility_bills),
                    "kyc_doc": bool(listing.kyc_doc)
                }
            }
            
            # Prepare user data
            try:
                profile = user.profile
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "kyc_verified": profile.kyc_verified,
                    "phone": profile.phone,
                    "wallet_address": profile.wallet_address
                }
            except Profile.DoesNotExist:
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "kyc_verified": False,
                    "phone": "",
                    "wallet_address": ""
                }
            
            # Call validation service
            request = {
                "listing_data": listing_data,
                "user_data": user_data
            }
            
            result = self.validation_service.validate_property(request)
            
            if result.get("success"):
                return result["result"]
            else:
                logger.error(f"Validation service error: {result.get('error')}")
                return {
                    "status": "ERROR",
                    "reasons": [result.get("error", "Unknown error")],
                    "listing_id": listing.id,
                    "user_id": user.id
                }
                
        except Exception as e:
            logger.error(f"Validation client error: {e}")
            return {
                "status": "ERROR",
                "reasons": [f"Client error: {str(e)}"],
                "listing_id": listing.id,
                "user_id": user.id
            }
    
    def calculate_valuation(self, listing: Listing) -> Dict[str, Any]:
        """
        Calculate property valuation using the Valuation Agent
        
        Args:
            listing: Django Listing model instance
            
        Returns:
            Valuation result dictionary
        """
        if not AGENTS_AVAILABLE:
            # Fallback valuation without MeTTa agents
            return self._fallback_valuation(listing)
        
        try:
            # Prepare listing data
            listing_data = {
                "id": listing.id,
                "title": listing.title,
                "description": listing.description,
                "location": listing.location,
                "property_type": listing.property_type,
                "size": float(listing.size) if listing.size else 0,
                "bedrooms": listing.bedrooms,
                "year_built": listing.year_built,
                "ownership_type": listing.ownership_type,
                "price": float(listing.price) if listing.price else 0
            }
            
            # Call valuation service
            request = {
                "listing_data": listing_data
            }
            
            result = self.valuation_service.calculate_property_value(request)
            
            if result.get("success"):
                return result["result"]
            else:
                logger.error(f"Valuation service error: {result.get('error')}")
                return {
                    "listing_id": listing.id,
                    "valuation_range": {"min": 0, "max": 0, "currency": "INR"},
                    "market_analysis": {"error": result.get("error", "Unknown error")},
                    "confidence_score": 0.0
                }
                
        except Exception as e:
            logger.error(f"Valuation client error: {e}")
            return {
                "listing_id": listing.id,
                "valuation_range": {"min": 0, "max": 0, "currency": "INR"},
                "market_analysis": {"error": f"Client error: {str(e)}"},
                "confidence_score": 0.0
            }
    
    def get_recommendations(self, user: User, limit: int = 5) -> Dict[str, Any]:
        """
        Get property recommendations using the Recommendation Agent
        
        Args:
            user: Django User model instance
            limit: Maximum number of recommendations
            
        Returns:
            Recommendation result dictionary
        """
        if not AGENTS_AVAILABLE:
            # Fallback recommendations without MeTTa agents
            return self._fallback_recommendations(user, limit)
        
        try:
            # Get available listings
            available_listings = Listing.objects.filter(status='submitted').values(
                'id', 'title', 'description', 'location', 'property_type', 
                'size', 'bedrooms', 'year_built', 'price'
            )
            
            # Prepare user data
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "viewed_properties": self._get_user_viewed_properties(user),
                "purchased_properties": self._get_user_purchased_properties(user),
                "favorited_properties": self._get_user_favorited_properties(user)
            }
            
            # Call recommendation service
            request = {
                "user_data": user_data,
                "available_listings": list(available_listings),
                "limit": limit
            }
            
            result = self.recommendation_service.get_property_recommendations(request)
            
            if result.get("success"):
                return result["result"]
            else:
                logger.error(f"Recommendation service error: {result.get('error')}")
                return {
                    "user_id": user.id,
                    "recommendations": [],
                    "reasoning": {"error": result.get("error", "Unknown error")},
                    "total_available": len(available_listings)
                }
                
        except Exception as e:
            logger.error(f"Recommendation client error: {e}")
            return {
                "user_id": user.id,
                "recommendations": [],
                "reasoning": {"error": f"Client error: {str(e)}"},
                "total_available": 0
            }
    
    def _get_user_viewed_properties(self, user: User) -> List[int]:
        """Get list of property IDs viewed by user"""
        # This would be implemented based on your user activity tracking
        # For now, return empty list
        return []
    
    def _get_user_purchased_properties(self, user: User) -> List[int]:
        """Get list of property IDs purchased by user"""
        # This would be implemented based on your purchase tracking
        # For now, return empty list
        return []
    
    def _get_user_favorited_properties(self, user: User) -> List[int]:
        """Get list of property IDs favorited by user"""
        # This would be implemented based on your favorites tracking
        # For now, return empty list
        return []
    
    def _fallback_validation(self, listing: Listing, user: User) -> Dict[str, Any]:
        """Fallback validation when MeTTa agents are not available"""
        try:
            # Check if user has profile and KYC
            try:
                profile = user.profile
                kyc_verified = profile.kyc_verified
            except Profile.DoesNotExist:
                kyc_verified = False
            
            # Document validation checks
            document_checks = {
                "title_deed": bool(listing.title_deed),
                "tax_certificate": bool(listing.tax_certificate),
                "utility_bills": bool(listing.utility_bills),
                "kyc_doc": bool(listing.kyc_doc)
            }
            
            # Basic property information checks
            basic_info_checks = {
                "title": bool(listing.title and listing.title.strip()),
                "description": bool(listing.description and listing.description.strip()),
                "location": bool(listing.location and listing.location.strip()),
                "property_type": bool(listing.property_type and listing.property_type.strip())
            }
            
            # Property size and details validation
            property_details_checks = {
                "size": bool(listing.size and float(listing.size) > 0),
                "bedrooms": bool(listing.bedrooms and listing.bedrooms > 0),
                "price": bool(listing.price and float(listing.price) > 0)
            }
            
            # Count valid checks
            valid_documents = sum(document_checks.values())
            valid_basic_info = sum(basic_info_checks.values())
            valid_property_details = sum(property_details_checks.values())
            
            # Determine validation status
            reasons = []
            status = "APPROVED"
            
            # KYC check
            if not kyc_verified:
                status = "REJECTED"
                reasons.append("KYC verification required")
            
            # Document checks (require all 4 documents for approval)
            if valid_documents < 4:
                status = "REJECTED"
                missing_docs = [doc for doc, valid in document_checks.items() if not valid]
                reasons.append(f"All 4 documents required. Missing: {', '.join(missing_docs)}")
            
            # Basic info checks (require all 4 fields)
            if valid_basic_info < 4:
                status = "REJECTED"
                missing_info = [info for info, valid in basic_info_checks.items() if not valid]
                reasons.append(f"All property information required. Missing: {', '.join(missing_info)}")
            
            # Property details checks (require at least 2 out of 3)
            if valid_property_details < 2:
                status = "REJECTED"
                reasons.append("Property details incomplete (size, bedrooms, price required)")
            
            # Additional content validation checks
            content_issues = []
            
            # Check if title is meaningful (not just "idk" or similar)
            if listing.title and len(listing.title.strip()) < 3:
                content_issues.append("Property title too short")
            
            # Check if description is meaningful
            if listing.description and len(listing.description.strip()) < 10:
                content_issues.append("Property description too short")
            
            # Check if location is specific enough
            if listing.location and len(listing.location.strip()) < 3:
                content_issues.append("Property location too vague")
            
            # Enhanced document content validation
            document_content_issues = []
            
            # Check for suspicious document names (random uploads)
            suspicious_patterns = ['screenshot', 'image', 'photo', 'random', 'test', 'sample', 'dummy', 'fake']
            
            if listing.title_deed:
                filename = listing.title_deed.name.lower()
                if any(pattern in filename for pattern in suspicious_patterns):
                    document_content_issues.append("Title deed appears to be a random document")
            
            if listing.tax_certificate:
                filename = listing.tax_certificate.name.lower()
                if any(pattern in filename for pattern in suspicious_patterns):
                    document_content_issues.append("Tax certificate appears to be a random document")
            
            if listing.utility_bills:
                filename = listing.utility_bills.name.lower()
                if any(pattern in filename for pattern in suspicious_patterns):
                    document_content_issues.append("Utility bills appear to be random documents")
            
            if listing.kyc_doc:
                filename = listing.kyc_doc.name.lower()
                if any(pattern in filename for pattern in suspicious_patterns):
                    document_content_issues.append("KYC document appears to be a random document")
            
            # Check for very small file sizes (likely random images)
            min_file_size = 50000  # 50KB minimum
            
            if listing.title_deed and listing.title_deed.size < min_file_size:
                document_content_issues.append("Title deed file too small (likely not a real document)")
            
            if listing.tax_certificate and listing.tax_certificate.size < min_file_size:
                document_content_issues.append("Tax certificate file too small (likely not a real document)")
            
            if listing.utility_bills and listing.utility_bills.size < min_file_size:
                document_content_issues.append("Utility bills file too small (likely not a real document)")
            
            if listing.kyc_doc and listing.kyc_doc.size < min_file_size:
                document_content_issues.append("KYC document file too small (likely not a real document)")
            
            if document_content_issues:
                status = "REJECTED"
                reasons.extend(document_content_issues)
            
            if content_issues:
                status = "REJECTED"
                reasons.extend(content_issues)
            
            # If all critical checks pass, approve
            if kyc_verified and valid_documents == 4 and valid_basic_info == 4 and valid_property_details >= 2 and not content_issues and not document_content_issues:
                status = "APPROVED"
                reasons = ["All validation checks passed - documents and content verified"]
            
            return {
                "status": status,
                "reasons": reasons,
                "listing_id": listing.id,
                "user_id": user.id,
                "validation_details": {
                    "kyc_verified": kyc_verified,
                    "documents_valid": valid_documents,
                    "basic_info_valid": valid_basic_info,
                    "property_details_valid": valid_property_details,
                    "document_checks": document_checks,
                    "basic_info_checks": basic_info_checks,
                    "property_details_checks": property_details_checks
                },
                "timestamp": self._get_timestamp()
            }
                
        except Exception as e:
            return {
                "status": "ERROR",
                "reasons": [f"Fallback validation error: {str(e)}"],
                "listing_id": listing.id,
                "user_id": user.id,
                "timestamp": self._get_timestamp()
            }
    
    def _fallback_valuation(self, listing: Listing) -> Dict[str, Any]:
        """Fallback valuation when MeTTa agents are not available"""
        try:
            # Simple valuation based on size and location
            base_price_per_sqft = 500  # Default base price per sqft in USD
            
            # Adjust based on location (case insensitive)
            location_multipliers = {
                'delhi': 1.5,
                'mumbai': 2.0,
                'bangalore': 1.2,
                'chennai': 1.0,
                'hyderabad': 1.1,
                'pune': 1.3,
                'kolkata': 0.9,
                'ahmedabad': 0.8,
                'us': 1.8,
                'usa': 1.8,
                'united states': 1.8,
                'florida': 2.2,
                'california': 2.5,
                'texas': 1.6,
                'new york': 3.0
            }
            
            location = (listing.location or 'Unknown').lower()
            multiplier = 1.0
            
            # Check for location matches
            for loc_key, loc_mult in location_multipliers.items():
                if loc_key in location:
                    multiplier = loc_mult
                    break
            
            # Calculate base value
            size = float(listing.size) if listing.size else 1000
            base_value = size * base_price_per_sqft * multiplier
            
            # Add some variance
            min_value = base_value * 0.85
            max_value = base_value * 1.15
            
            return {
                "listing_id": listing.id,
                "valuation_range": {
                    "min": min_value,
                    "max": max_value,
                    "currency": "INR"
                },
                "market_analysis": {
                    "location_trend": "stable",
                    "property_type_demand": "moderate",
                    "market_conditions": "favorable"
                },
                "confidence_score": 0.6,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            return {
                "listing_id": listing.id,
                "valuation_range": {"min": 0, "max": 0, "currency": "INR"},
                "market_analysis": {"error": f"Fallback valuation error: {str(e)}"},
                "confidence_score": 0.0,
                "timestamp": self._get_timestamp()
            }
    
    def _fallback_recommendations(self, user: User, limit: int) -> Dict[str, Any]:
        """Fallback recommendations when MeTTa agents are not available"""
        try:
            # Get recent listings as recommendations
            available_listings = Listing.objects.filter(status='submitted').order_by('-created_at')[:limit]
            
            recommendations = []
            for listing in available_listings:
                recommendations.append({
                    "listing_id": listing.id,
                    "title": listing.title or f"Property #{listing.id}",
                    "location": listing.location or "Unknown",
                    "price": float(listing.price) if listing.price else 0,
                    "property_type": listing.property_type or "Unknown",
                    "size": float(listing.size) if listing.size else 0,
                    "bedrooms": listing.bedrooms or 0,
                    "recommendation_score": 0.5
                })
            
            return {
                "user_id": user.id,
                "recommendations": recommendations,
                "reasoning": {
                    "user_preferences": {},
                    "recommendation_factors": ["Recent listings"],
                    "similarity_analysis": {}
                },
                "total_available": len(available_listings),
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            return {
                "user_id": user.id,
                "recommendations": [],
                "reasoning": {"error": f"Fallback recommendation error: {str(e)}"},
                "total_available": 0,
                "timestamp": self._get_timestamp()
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

# Global agent client instance
agent_client = AgentClient()
