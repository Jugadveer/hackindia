;; Asset Validation Agent - MeTTa Rules
;; Purpose: Validate property listings before NFT minting

;; KYC Validation Rules
(= (kyc-verified ?user) (and 
    (has-profile ?user ?profile)
    (kyc-status ?profile "verified")))

;; Document Validation Rules
(= (has-required-docs ?listing) (and
    (has-document ?listing "title_deed")
    (has-document ?listing "tax_certificate")
    (has-document ?listing "utility_bills")
    (has-document ?listing "kyc_doc")))

;; Property Compliance Rules
(= (property-compliant ?listing) (and
    (has-minimum-area ?listing 500)  ; Minimum 500 sq ft
    (valid-property-type ?listing)
    (no-lien-flags ?listing)
    (zoning-compliant ?listing)))

;; Area Validation
(= (has-minimum-area ?listing ?min-area) 
    (and (listing-size ?listing ?size) 
         (> ?size ?min-area)))

;; Property Type Validation
(= (valid-property-type ?listing) (or
    (property-type ?listing "Apartment")
    (property-type ?listing "Villa")
    (property-type ?listing "Commercial")
    (property-type ?listing "Land")))

;; Zoning Compliance
(= (zoning-compliant ?listing) (and
    (property-type ?listing ?type)
    (location ?listing ?location)
    (allowed-zoning ?location ?type)))

;; Lien Check
(= (no-lien-flags ?listing) (not (has-lien ?listing)))

;; Main Validation Function
(= (validate-listing ?listing ?user) 
    (if (and (kyc-verified ?user) 
             (has-required-docs ?listing) 
             (property-compliant ?listing))
        "APPROVED"
        (if (not (kyc-verified ?user))
            "REJECTED: KYC not verified"
            (if (not (has-required-docs ?listing))
                "REJECTED: Missing required documents"
                (if (not (property-compliant ?listing))
                    "REJECTED: Property compliance issues"
                    "NEEDS_MORE_INFO")))))

;; Validation Reasons
(= (get-validation-reasons ?listing ?user) 
    (let ((kyc-ok (kyc-verified ?user))
          (docs-ok (has-required-docs ?listing))
          (compliant-ok (property-compliant ?listing)))
        (list 
            (if kyc-ok "KYC: ✓ Verified" "KYC: ✗ Not verified")
            (if docs-ok "Documents: ✓ Complete" "Documents: ✗ Missing required files")
            (if compliant-ok "Compliance: ✓ Valid" "Compliance: ✗ Issues found"))))

