"""
Valuation Service - SingularityNET Service Wrapper
Purpose: Estimate property market value using reasoning and stored knowledge
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

class ValuationService:
    def __init__(self):
        """Initialize the valuation service with MeTTa engine"""
        self.metta = MeTTa()
        self._load_valuation_rules()
        
    def _load_valuation_rules(self):
        """Load MeTTa valuation rules"""
        try:
            # Load the valuation agent rules
            import os
            from django.conf import settings
            metta_file_path = os.path.join(settings.BASE_DIR, 'agents', 'valuation_agent.metta')
            with open(metta_file_path, 'r') as f:
                rules = f.read()
            self.metta.load_module_from_string(rules)
            logger.info("Valuation rules loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load valuation rules: {e}")
            
    def calculate_valuation(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate property valuation
        
        Args:
            listing_data: Property listing information
            
        Returns:
            Valuation result with price range and reasoning
        """
        try:
            # Prepare facts for MeTTa
            facts = self._prepare_facts(listing_data)
            
            # Add facts to MeTTa knowledge base
            for fact in facts:
                self.metta.add_atom(fact)
                
            # Query valuation result
            result = self.metta.run("(final-valuation listing)")
            
            # Parse results
            valuation_range = self._parse_valuation_result(result)
            
            # Add market analysis
            market_analysis = self._get_market_analysis(listing_data)
            
            return {
                "listing_id": listing_data.get("id"),
                "valuation_range": valuation_range,
                "market_analysis": market_analysis,
                "confidence_score": self._calculate_confidence(listing_data),
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Valuation error: {e}")
            return {
                "listing_id": listing_data.get("id"),
                "valuation_range": {"min": 0, "max": 0, "currency": "INR"},
                "market_analysis": {"error": str(e)},
                "confidence_score": 0.0,
                "timestamp": self._get_timestamp()
            }
    
    def _prepare_facts(self, listing_data: Dict[str, Any]) -> List[str]:
        """Prepare MeTTa facts from listing data"""
        facts = []
        
        listing_id = listing_data.get("id", "listing")
        
        # Basic property facts
        facts.append(f"(location {listing_id} {listing_data.get('location', 'Unknown')})")
        facts.append(f"(property-type {listing_id} {listing_data.get('property_type', 'Unknown')})")
        facts.append(f"(listing-size {listing_id} {listing_data.get('size', 0)})")
        facts.append(f"(bedrooms {listing_id} {listing_data.get('bedrooms', 0)})")
        facts.append(f"(year-built {listing_id} {listing_data.get('year_built', 2020)})")
        
        # Area type (simplified - could be enhanced with actual area classification)
        location = listing_data.get('location', 'Unknown')
        area_type = self._determine_area_type(location)
        facts.append(f"(area-type {listing_id} {area_type})")
        
        # Market trend (simplified - could be enhanced with real market data)
        facts.append(f"(market-trend {location} stable)")
        
        return facts
    
    def _determine_area_type(self, location: str) -> str:
        """Determine area type based on location"""
        # Simplified logic - in production, this would use actual geographic data
        if any(keyword in location.lower() for keyword in ['central', 'downtown', 'city center']):
            return "Central"
        elif any(keyword in location.lower() for keyword in ['suburb', 'outskirts', 'peripheral']):
            return "Outer"
        else:
            return "Suburban"
    
    def _parse_valuation_result(self, result) -> Dict[str, Any]:
        """Parse MeTTa valuation result"""
        if not result:
            return {"min": 0, "max": 0, "currency": "INR"}
        
        try:
            # Extract valuation range from result
            result_str = str(result[0])
            
            # Parse the valuation range
            # Expected format: (valuation-range min_value max_value)
            if "valuation-range" in result_str:
                # Extract numeric values
                import re
                numbers = re.findall(r'\d+\.?\d*', result_str)
                if len(numbers) >= 2:
                    min_val = float(numbers[0])
                    max_val = float(numbers[1])
                    return {
                        "min": min_val,
                        "max": max_val,
                        "currency": "INR"
                    }
            
            return {"min": 0, "max": 0, "currency": "INR"}
            
        except Exception as e:
            logger.error(f"Error parsing valuation result: {e}")
            return {"min": 0, "max": 0, "currency": "INR"}
    
    def _get_market_analysis(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get market analysis for the property"""
        location = listing_data.get('location', 'Unknown')
        property_type = listing_data.get('property_type', 'Unknown')
        
        # Simplified market analysis
        analysis = {
            "location_trend": "stable",
            "property_type_demand": "moderate",
            "market_conditions": "favorable",
            "comparable_properties": self._get_comparable_properties(location, property_type),
            "price_per_sqft": self._get_price_per_sqft(location, property_type)
        }
        
        return analysis
    
    def _get_comparable_properties(self, location: str, property_type: str) -> List[Dict[str, Any]]:
        """Get comparable properties (simplified)"""
        # In production, this would query actual comparable sales data
        return [
            {
                "location": location,
                "type": property_type,
                "price_per_sqft": 8000,
                "sale_date": "2024-01-15"
            },
            {
                "location": location,
                "type": property_type,
                "price_per_sqft": 8500,
                "sale_date": "2024-02-20"
            }
        ]
    
    def _get_price_per_sqft(self, location: str, property_type: str) -> float:
        """Get base price per square foot"""
        # Simplified pricing - in production, this would use real market data
        base_rates = {
            ("Delhi", "Apartment"): 8000,
            ("Delhi", "Villa"): 12000,
            ("Mumbai", "Apartment"): 15000,
            ("Mumbai", "Villa"): 25000,
            ("Bangalore", "Apartment"): 6000,
            ("Bangalore", "Villa"): 10000,
        }
        
        return base_rates.get((location, property_type), 5000)
    
    def _calculate_confidence(self, listing_data: Dict[str, Any]) -> float:
        """Calculate confidence score for the valuation"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on data completeness
        if listing_data.get('size'):
            confidence += 0.1
        if listing_data.get('bedrooms'):
            confidence += 0.1
        if listing_data.get('year_built'):
            confidence += 0.1
        if listing_data.get('location'):
            confidence += 0.1
        if listing_data.get('property_type'):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

# SingularityNET Service Interface
class ValuationServiceInterface:
    def __init__(self):
        self.service = ValuationService()
    
    def calculate_property_value(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        SingularityNET service endpoint for property valuation
        
        Args:
            request: JSON request containing listing_data
            
        Returns:
            JSON response with valuation results
        """
        try:
            listing_data = request.get("listing_data", {})
            
            result = self.service.calculate_valuation(listing_data)
            
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
                    "listing_id": request.get("listing_data", {}).get("id"),
                    "valuation_range": {"min": 0, "max": 0, "currency": "INR"},
                    "market_analysis": {"error": str(e)},
                    "confidence_score": 0.0
                }
            }

# Export for SingularityNET
valuation_service = ValuationServiceInterface()
