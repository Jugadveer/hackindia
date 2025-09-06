"""
Asset Validation Service - SingularityNET Service Wrapper
Purpose: Validate property listings before NFT minting
"""

import json
import logging
from typing import Dict, Any, List
from hyperon import MeTTa
from hyperon.atoms import OperationAtom, E
from hyperon.ext import register_atoms

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationService:
    def __init__(self):
        """Initialize the validation service with MeTTa engine"""
        self.metta = MeTTa()
        self._load_validation_rules()
        
    def _load_validation_rules(self):
        """Load MeTTa validation rules"""
        try:
            # Load the validation agent rules
            import os
            from django.conf import settings
            metta_file_path = os.path.join(settings.BASE_DIR, 'agents', 'validation_agent.metta')
            with open(metta_file_path, 'r') as f:
                rules = f.read()
            self.metta.load_module_from_string(rules)
            logger.info("Validation rules loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load validation rules: {e}")
            
    def validate_listing(self, listing_data: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a property listing
        
        Args:
            listing_data: Property listing information
            user_data: User profile and KYC information
            
        Returns:
            Validation result with status and reasons
        """
        try:
            # Prepare facts for MeTTa
            facts = self._prepare_facts(listing_data, user_data)
            
            # Add facts to MeTTa knowledge base
            for fact in facts:
                self.metta.add_atom(fact)
                
            # Query validation result
            result = self.metta.run("(validate-listing listing user)")
            
            # Get validation reasons
            reasons = self.metta.run("(get-validation-reasons listing user)")
            
            # Parse results
            validation_status = self._parse_validation_result(result)
            validation_reasons = self._parse_reasons(reasons)
            
            return {
                "status": validation_status,
                "reasons": validation_reasons,
                "listing_id": listing_data.get("id"),
                "user_id": user_data.get("id"),
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "status": "ERROR",
                "reasons": [f"Validation failed: {str(e)}"],
                "listing_id": listing_data.get("id"),
                "user_id": user_data.get("id"),
                "timestamp": self._get_timestamp()
            }
    
    def _prepare_facts(self, listing_data: Dict[str, Any], user_data: Dict[str, Any]) -> List[str]:
        """Prepare MeTTa facts from listing and user data"""
        facts = []
        
        # User facts
        user_id = user_data.get("id")
        kyc_verified = user_data.get("kyc_verified", False)
        facts.append(f"(has-profile {user_id} profile_{user_id})")
        facts.append(f"(kyc-status profile_{user_id} {'verified' if kyc_verified else 'pending'})")
        
        # Listing facts
        listing_id = listing_data.get("id")
        facts.append(f"(listing-size {listing_id} {listing_data.get('size', 0)})")
        facts.append(f"(property-type {listing_id} {listing_data.get('property_type', 'Unknown')})")
        facts.append(f"(location {listing_id} {listing_data.get('location', 'Unknown')})")
        
        # Document facts
        documents = listing_data.get("documents", {})
        for doc_type in ["title_deed", "tax_certificate", "utility_bills", "kyc_doc"]:
            if documents.get(doc_type):
                facts.append(f"(has-document {listing_id} {doc_type})")
        
        # Compliance facts
        facts.append(f"(has-lien {listing_id} false)")  # Assume no liens for now
        facts.append(f"(allowed-zoning {listing_data.get('location', 'Unknown')} {listing_data.get('property_type', 'Unknown')})")
        
        return facts
    
    def _parse_validation_result(self, result) -> str:
        """Parse MeTTa validation result"""
        if not result:
            return "NEEDS_MORE_INFO"
        
        # Extract status from result
        result_str = str(result[0]) if result else "NEEDS_MORE_INFO"
        
        if "APPROVED" in result_str:
            return "APPROVED"
        elif "REJECTED" in result_str:
            return "REJECTED"
        else:
            return "NEEDS_MORE_INFO"
    
    def _parse_reasons(self, reasons) -> List[str]:
        """Parse validation reasons"""
        if not reasons:
            return ["No specific reasons provided"]
        
        reason_list = []
        for reason in reasons:
            reason_str = str(reason)
            if "KYC" in reason_str:
                reason_list.append("KYC verification status")
            elif "Documents" in reason_str:
                reason_list.append("Required document completeness")
            elif "Compliance" in reason_str:
                reason_list.append("Property compliance validation")
        
        return reason_list if reason_list else ["General validation check"]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

# SingularityNET Service Interface
class ValidationServiceInterface:
    def __init__(self):
        self.service = ValidationService()
    
    def validate_property(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        SingularityNET service endpoint for property validation
        
        Args:
            request: JSON request containing listing_data and user_data
            
        Returns:
            JSON response with validation results
        """
        try:
            listing_data = request.get("listing_data", {})
            user_data = request.get("user_data", {})
            
            result = self.service.validate_listing(listing_data, user_data)
            
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
                    "status": "ERROR",
                    "reasons": [f"Service error: {str(e)}"]
                }
            }

# Export for SingularityNET
validation_service = ValidationServiceInterface()
