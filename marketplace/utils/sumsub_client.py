"""
Sumsub KYC Verification Client
Handles all interactions with Sumsub API for KYC verification
"""

import hashlib
import hmac
import time
import requests
import logging
from django.conf import settings
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SumsubClient:
    """Client for Sumsub KYC verification API"""
    
    def __init__(self):
        self.app_token = settings.SUMSUB_APP_TOKEN
        self.secret_key = settings.SUMSUB_SECRET_KEY
        self.base_url = settings.SUMSUB_BASE_URL
        self.timeout = 30
    
    def _create_signature(self, method: str, url: str, body: str = "", timestamp: int = None) -> str:
        """Create HMAC signature for Sumsub API authentication"""
        if timestamp is None:
            timestamp = int(time.time())
        
        # Create the string to sign
        string_to_sign = f"{method.upper()}{url}{body}{timestamp}"
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_headers(self, method: str, url: str, body: str = "") -> Dict[str, str]:
        """Get headers for Sumsub API request"""
        timestamp = int(time.time())
        signature = self._create_signature(method, url, body, timestamp)
        
        return {
            'X-App-Token': self.app_token,
            'X-App-Access-Ts': str(timestamp),
            'X-App-Access-Sig': signature,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def create_applicant(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new applicant in Sumsub"""
        try:
            url = f"{self.base_url}/resources/applicants"
            
            # Prepare applicant data
            applicant_data = {
                "externalUserId": user_id,
                "info": {
                    "firstName": user_data.get('first_name', ''),
                    "lastName": user_data.get('last_name', ''),
                    "email": user_data.get('email', ''),
                    "phone": user_data.get('phone', ''),
                    "country": user_data.get('country', 'US'),
                    "dob": user_data.get('dob', ''),
                }
            }
            
            headers = self._get_headers('POST', url, str(applicant_data))
            
            response = requests.post(
                url,
                json=applicant_data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json(),
                    'applicant_id': response.json().get('id')
                }
            else:
                logger.error(f"Sumsub create applicant error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Failed to create applicant: {response.text}",
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Sumsub create applicant exception: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_access_token(self, user_id: str, level_name: str = "basic-kyc-level") -> Dict[str, Any]:
        """Get access token for applicant verification session"""
        try:
            url = f"{self.base_url}/resources/accessTokens"
            
            token_data = {
                "userId": user_id,
                "ttlInSecs": 600,  # 10 minutes
                "levelName": level_name
            }
            
            headers = self._get_headers('POST', url, str(token_data))
            
            response = requests.post(
                url,
                json=token_data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json(),
                    'token': response.json().get('token')
                }
            else:
                logger.error(f"Sumsub access token error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Failed to get access token: {response.text}",
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Sumsub access token exception: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_applicant_status(self, user_id: str) -> Dict[str, Any]:
        """Get applicant verification status"""
        try:
            url = f"{self.base_url}/resources/applicants/{user_id}/status"
            
            headers = self._get_headers('GET', url)
            
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': data,
                    'status': data.get('reviewResult', {}).get('reviewAnswer', 'UNKNOWN'),
                    'verification_status': data.get('reviewResult', {}).get('reviewAnswer', 'UNKNOWN')
                }
            else:
                logger.error(f"Sumsub status error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Failed to get status: {response.text}",
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Sumsub status exception: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_document(self, user_id: str, document_file, document_type: str = "ID_CARD") -> Dict[str, Any]:
        """Upload document for verification"""
        try:
            url = f"{self.base_url}/resources/applicants/{user_id}/info/idDoc"
            
            # Prepare file data
            files = {
                'content': (document_file.name, document_file.read(), document_file.content_type)
            }
            
            data = {
                'idDocType': document_type,
                'idDocSubType': 'FRONT'
            }
            
            # For file uploads, we need different headers
            timestamp = int(time.time())
            signature = self._create_signature('POST', url, "", timestamp)
            
            headers = {
                'X-App-Token': self.app_token,
                'X-App-Access-Ts': str(timestamp),
                'X-App-Access-Sig': signature,
            }
            
            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                logger.error(f"Sumsub upload error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Failed to upload document: {response.text}",
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Sumsub upload exception: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def initiate_verification(self, user_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate complete KYC verification process"""
        try:
            # Step 1: Create applicant
            applicant_result = self.create_applicant(user_id, user_data)
            if not applicant_result['success']:
                return applicant_result
            
            # Step 2: Get access token
            token_result = self.get_access_token(user_id)
            if not token_result['success']:
                return token_result
            
            return {
                'success': True,
                'applicant_id': applicant_result.get('applicant_id'),
                'access_token': token_result.get('token'),
                'verification_url': f"https://api.sumsub.com/idensic/static/sumsub-kyc.js?accessToken={token_result.get('token')}"
            }
            
        except Exception as e:
            logger.error(f"Sumsub initiate verification exception: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_verification_status(self, user_id: str) -> Dict[str, Any]:
        """Check if user's KYC verification is complete and approved"""
        try:
            status_result = self.get_applicant_status(user_id)
            if not status_result['success']:
                return status_result
            
            verification_status = status_result.get('verification_status', 'UNKNOWN')
            
            # Map Sumsub statuses to our internal statuses
            if verification_status == 'GREEN':
                return {
                    'success': True,
                    'verified': True,
                    'status': 'APPROVED',
                    'message': 'KYC verification approved'
                }
            elif verification_status == 'RED':
                return {
                    'success': True,
                    'verified': False,
                    'status': 'REJECTED',
                    'message': 'KYC verification rejected'
                }
            elif verification_status == 'YELLOW':
                return {
                    'success': True,
                    'verified': False,
                    'status': 'PENDING',
                    'message': 'KYC verification pending review'
                }
            else:
                return {
                    'success': True,
                    'verified': False,
                    'status': 'UNKNOWN',
                    'message': 'KYC verification status unknown'
                }
                
        except Exception as e:
            logger.error(f"Sumsub check status exception: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
sumsub_client = SumsubClient()

