import os
import logging
from PIL import Image
import PyPDF2
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)

class KYCValidator:
    """Smart KYC document validation and auto-approval system"""
    
    def __init__(self):
        self.auto_approval_enabled = getattr(settings, 'KYC_AUTO_APPROVAL_ENABLED', True)
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        
    def validate_document(self, uploaded_file: UploadedFile) -> dict:
        """
        Validate KYC document and determine if it can be auto-approved
        
        Returns:
            dict: {
                'valid': bool,
                'auto_approve': bool,
                'confidence_score': float (0-1),
                'reasons': list,
                'errors': list
            }
        """
        result = {
            'valid': False,
            'auto_approve': False,
            'confidence_score': 0.0,
            'reasons': [],
            'errors': []
        }
        
        try:
            # Basic file validation
            basic_validation = self._validate_basic_file(uploaded_file)
            if not basic_validation['valid']:
                result['errors'].extend(basic_validation['errors'])
                return result
            
            result['valid'] = True
            result['reasons'].extend(basic_validation['reasons'])
            
            # Document content validation
            content_validation = self._validate_document_content(uploaded_file)
            result['reasons'].extend(content_validation['reasons'])
            result['errors'].extend(content_validation['errors'])
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                basic_validation, content_validation
            )
            result['confidence_score'] = confidence_score
            
            # Determine auto-approval
            if self.auto_approval_enabled and confidence_score >= 0.8:
                result['auto_approve'] = True
                result['reasons'].append("Document meets auto-approval criteria")
            else:
                result['reasons'].append("Document requires manual review")
                
        except Exception as e:
            logger.error(f"KYC validation error: {e}")
            result['errors'].append(f"Validation error: {str(e)}")
            
        return result
    
    def _validate_basic_file(self, uploaded_file: UploadedFile) -> dict:
        """Basic file validation (size, extension, etc.)"""
        result = {'valid': True, 'reasons': [], 'errors': []}
        
        # Check file size
        if uploaded_file.size > self.max_file_size:
            result['valid'] = False
            result['errors'].append(f"File too large: {uploaded_file.size / (1024*1024):.1f}MB (max 10MB)")
        else:
            result['reasons'].append(f"File size OK: {uploaded_file.size / (1024*1024):.1f}MB")
        
        # Check file extension
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in self.allowed_extensions:
            result['valid'] = False
            result['errors'].append(f"Invalid file type: {file_ext}")
        else:
            result['reasons'].append(f"Valid file type: {file_ext}")
        
        # Check if file is not empty
        if uploaded_file.size == 0:
            result['valid'] = False
            result['errors'].append("File is empty")
        else:
            result['reasons'].append("File is not empty")
            
        return result
    
    def _validate_document_content(self, uploaded_file: UploadedFile) -> dict:
        """Validate document content for authenticity"""
        result = {'reasons': [], 'errors': []}
        
        try:
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            
            if file_ext == '.pdf':
                pdf_validation = self._validate_pdf_content(uploaded_file)
                result['reasons'].extend(pdf_validation['reasons'])
                result['errors'].extend(pdf_validation['errors'])
                
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                image_validation = self._validate_image_content(uploaded_file)
                result['reasons'].extend(image_validation['reasons'])
                result['errors'].extend(image_validation['errors'])
                
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            result['errors'].append(f"Content validation failed: {str(e)}")
            
        return result
    
    def _validate_pdf_content(self, uploaded_file: UploadedFile) -> dict:
        """Validate PDF document content"""
        result = {'reasons': [], 'errors': []}
        
        try:
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Try to read PDF
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            
            if len(pdf_reader.pages) == 0:
                result['errors'].append("PDF has no pages")
            else:
                result['reasons'].append(f"PDF has {len(pdf_reader.pages)} page(s)")
                
                # Try to extract text from first page
                try:
                    first_page = pdf_reader.pages[0]
                    text = first_page.extract_text()
                    
                    if len(text.strip()) > 10:
                        result['reasons'].append("PDF contains readable text")
                        
                        # Check for common ID document keywords
                        id_keywords = ['passport', 'license', 'id', 'identity', 'government', 'issued']
                        found_keywords = [kw for kw in id_keywords if kw.lower() in text.lower()]
                        
                        if found_keywords:
                            result['reasons'].append(f"Contains ID keywords: {', '.join(found_keywords)}")
                        else:
                            result['errors'].append("No ID document keywords found")
                    else:
                        result['errors'].append("PDF text is too short or unreadable")
                        
                except Exception as e:
                    result['errors'].append(f"Could not extract PDF text: {str(e)}")
                    
        except Exception as e:
            result['errors'].append(f"PDF validation failed: {str(e)}")
            
        return result
    
    def _validate_image_content(self, uploaded_file: UploadedFile) -> dict:
        """Validate image document content"""
        result = {'reasons': [], 'errors': []}
        
        try:
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Open image with PIL
            image = Image.open(uploaded_file)
            
            # Check image dimensions
            width, height = image.size
            if width < 200 or height < 200:
                result['errors'].append(f"Image too small: {width}x{height}")
            else:
                result['reasons'].append(f"Image size OK: {width}x{height}")
            
            # Check image format
            if image.format not in ['JPEG', 'PNG']:
                result['errors'].append(f"Unsupported image format: {image.format}")
            else:
                result['reasons'].append(f"Valid image format: {image.format}")
            
            # Check if image is not corrupted
            try:
                image.verify()
                result['reasons'].append("Image is not corrupted")
            except Exception:
                result['errors'].append("Image appears to be corrupted")
                
        except Exception as e:
            result['errors'].append(f"Image validation failed: {str(e)}")
            
        return result
    
    def _calculate_confidence_score(self, basic_validation: dict, content_validation: dict) -> float:
        """Calculate confidence score for auto-approval"""
        score = 0.0
        
        # Basic validation contributes 40% of the score
        if basic_validation['valid']:
            score += 0.4
        
        # Content validation contributes 60% of the score
        reasons_count = len(content_validation['reasons'])
        errors_count = len(content_validation['errors'])
        
        if reasons_count > 0:
            # More reasons = higher confidence
            content_score = min(0.6, reasons_count * 0.1)
            # Penalize errors
            error_penalty = min(0.3, errors_count * 0.1)
            score += max(0, content_score - error_penalty)
        
        return min(1.0, score)

# Global validator instance
kyc_validator = KYCValidator()
