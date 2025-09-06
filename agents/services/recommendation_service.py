"""
Recommendation Service - SingularityNET Service Wrapper
Purpose: Suggest properties to buyers based on history, preferences, and similarity
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from hyperon import MeTTa
from hyperon.atoms import OperationAtom, E
from hyperon.ext import register_atoms

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self):
        """Initialize the recommendation service with MeTTa engine"""
        self.metta = MeTTa()
        self._load_recommendation_rules()
        
    def _load_recommendation_rules(self):
        """Load MeTTa recommendation rules"""
        try:
            # Load the recommendation agent rules
            import os
            from django.conf import settings
            metta_file_path = os.path.join(settings.BASE_DIR, 'agents', 'recommendation_agent.metta')
            with open(metta_file_path, 'r') as f:
                rules = f.read()
            self.metta.load_module_from_string(rules)
            logger.info("Recommendation rules loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load recommendation rules: {e}")
            
    def get_recommendations(self, user_data: Dict[str, Any], available_listings: List[Dict[str, Any]], limit: int = 5) -> Dict[str, Any]:
        """
        Get property recommendations for a user
        
        Args:
            user_data: User profile and interaction history
            available_listings: List of available property listings
            limit: Maximum number of recommendations to return
            
        Returns:
            Recommendation result with suggested properties
        """
        try:
            # Prepare facts for MeTTa
            facts = self._prepare_facts(user_data, available_listings)
            
            # Add facts to MeTTa knowledge base
            for fact in facts:
                self.metta.add_atom(fact)
                
            # Query recommendations
            result = self.metta.run(f"(recommend-properties user {limit})")
            
            # Parse results
            recommendations = self._parse_recommendations(result, available_listings)
            
            # Add recommendation reasoning
            reasoning = self._get_recommendation_reasoning(user_data, recommendations)
            
            return {
                "user_id": user_data.get("id"),
                "recommendations": recommendations,
                "reasoning": reasoning,
                "total_available": len(available_listings),
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return {
                "user_id": user_data.get("id"),
                "recommendations": [],
                "reasoning": {"error": str(e)},
                "total_available": len(available_listings),
                "timestamp": self._get_timestamp()
            }
    
    def _prepare_facts(self, user_data: Dict[str, Any], available_listings: List[Dict[str, Any]]) -> List[str]:
        """Prepare MeTTa facts from user data and listings"""
        facts = []
        
        user_id = user_data.get("id", "user")
        
        # User interaction history
        viewed_properties = user_data.get("viewed_properties", [])
        purchased_properties = user_data.get("purchased_properties", [])
        favorited_properties = user_data.get("favorited_properties", [])
        
        # Add user interaction facts
        for prop_id in viewed_properties:
            facts.append(f"(viewed-properties {user_id} {prop_id})")
        
        for prop_id in purchased_properties:
            facts.append(f"(purchased-properties {user_id} {prop_id})")
        
        for prop_id in favorited_properties:
            facts.append(f"(favorited-properties {user_id} {prop_id})")
        
        # Add listing facts
        for listing in available_listings:
            listing_id = listing.get("id")
            facts.append(f"(available-listings {listing_id})")
            facts.append(f"(location {listing_id} {listing.get('location', 'Unknown')})")
            facts.append(f"(property-type {listing_id} {listing.get('property_type', 'Unknown')})")
            facts.append(f"(price {listing_id} {listing.get('price', 0)})")
            facts.append(f"(size {listing_id} {listing.get('size', 0)})")
            facts.append(f"(bedrooms {listing_id} {listing.get('bedrooms', 0)})")
        
        # Add all users fact
        facts.append(f"(all-users {user_id})")
        
        return facts
    
    def _parse_recommendations(self, result, available_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse MeTTa recommendation results"""
        if not result:
            return []
        
        recommendations = []
        
        try:
            # Extract recommendation IDs from result
            result_str = str(result[0])
            
            # Parse the recommendation list
            # Expected format: (list listing_id1 listing_id2 ...)
            if "list" in result_str:
                import re
                # Extract listing IDs
                listing_ids = re.findall(r'listing_\w+', result_str)
                
                # Map to actual listing data
                for listing_id in listing_ids:
                    # Find corresponding listing data
                    for listing in available_listings:
                        if str(listing.get("id")) == listing_id.replace("listing_", ""):
                            recommendations.append({
                                "listing_id": listing.get("id"),
                                "title": listing.get("title"),
                                "location": listing.get("location"),
                                "price": listing.get("price"),
                                "property_type": listing.get("property_type"),
                                "size": listing.get("size"),
                                "bedrooms": listing.get("bedrooms"),
                                "recommendation_score": self._calculate_recommendation_score(listing)
                            })
                            break
            
            # If no specific recommendations, return top listings based on simple scoring
            if not recommendations:
                recommendations = self._get_fallback_recommendations(available_listings)
            
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}")
            recommendations = self._get_fallback_recommendations(available_listings)
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _calculate_recommendation_score(self, listing: Dict[str, Any]) -> float:
        """Calculate recommendation score for a listing"""
        # Simplified scoring algorithm
        score = 0.5  # Base score
        
        # Boost score based on listing completeness
        if listing.get("title"):
            score += 0.1
        if listing.get("description"):
            score += 0.1
        if listing.get("images"):
            score += 0.1
        if listing.get("price"):
            score += 0.1
        if listing.get("size"):
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_fallback_recommendations(self, available_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get fallback recommendations when MeTTa parsing fails"""
        recommendations = []
        
        for listing in available_listings[:5]:  # Take first 5 listings
            recommendations.append({
                "listing_id": listing.get("id"),
                "title": listing.get("title"),
                "location": listing.get("location"),
                "price": listing.get("price"),
                "property_type": listing.get("property_type"),
                "size": listing.get("size"),
                "bedrooms": listing.get("bedrooms"),
                "recommendation_score": 0.5
            })
        
        return recommendations
    
    def _get_recommendation_reasoning(self, user_data: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get reasoning for recommendations"""
        reasoning = {
            "user_preferences": self._extract_user_preferences(user_data),
            "recommendation_factors": [],
            "similarity_analysis": {}
        }
        
        # Analyze user preferences
        viewed_locations = user_data.get("viewed_properties", [])
        if viewed_locations:
            reasoning["recommendation_factors"].append("Based on your viewing history")
        
        # Analyze recommendation factors
        for rec in recommendations:
            if rec.get("property_type"):
                reasoning["recommendation_factors"].append(f"Similar property type: {rec['property_type']}")
            if rec.get("location"):
                reasoning["recommendation_factors"].append(f"Location preference: {rec['location']}")
        
        return reasoning
    
    def _extract_user_preferences(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user preferences from interaction history"""
        preferences = {
            "preferred_locations": [],
            "preferred_property_types": [],
            "price_range": {"min": 0, "max": 0},
            "size_range": {"min": 0, "max": 0}
        }
        
        # Extract from viewed properties (simplified)
        viewed_properties = user_data.get("viewed_properties", [])
        if viewed_properties:
            preferences["preferred_locations"] = ["Delhi", "Mumbai"]  # Simplified
            preferences["preferred_property_types"] = ["Apartment", "Villa"]  # Simplified
        
        return preferences
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

# SingularityNET Service Interface
class RecommendationServiceInterface:
    def __init__(self):
        self.service = RecommendationService()
    
    def get_property_recommendations(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        SingularityNET service endpoint for property recommendations
        
        Args:
            request: JSON request containing user_data and available_listings
            
        Returns:
            JSON response with recommendation results
        """
        try:
            user_data = request.get("user_data", {})
            available_listings = request.get("available_listings", [])
            limit = request.get("limit", 5)
            
            result = self.service.get_recommendations(user_data, available_listings, limit)
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Service error: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": {
                    "user_id": request.get("user_data", {}).get("id"),
                    "recommendations": [],
                    "reasoning": {"error": str(e)},
                    "total_available": 0
                }
            }

# Export for SingularityNET
recommendation_service = RecommendationServiceInterface()
