;; Valuation Agent - MeTTa Rules
;; Purpose: Estimate property market value using reasoning and stored knowledge

;; Base Rate per Square Foot by Location and Type
(= (base-rate-per-sqft "Delhi" "Apartment") 8000)
(= (base-rate-per-sqft "Delhi" "Villa") 12000)
(= (base-rate-per-sqft "Delhi" "Commercial") 15000)
(= (base-rate-per-sqft "Delhi" "Land") 5000)

(= (base-rate-per-sqft "Mumbai" "Apartment") 15000)
(= (base-rate-per-sqft "Mumbai" "Villa") 25000)
(= (base-rate-per-sqft "Mumbai" "Commercial") 30000)
(= (base-rate-per-sqft "Mumbai" "Land") 8000)

(= (base-rate-per-sqft "Bangalore" "Apartment") 6000)
(= (base-rate-per-sqft "Bangalore" "Villa") 10000)
(= (base-rate-per-sqft "Bangalore" "Commercial") 12000)
(= (base-rate-per-sqft "Bangalore" "Land") 4000)

(= (base-rate-per-sqft "Chennai" "Apartment") 5000)
(= (base-rate-per-sqft "Chennai" "Villa") 8000)
(= (base-rate-per-sqft "Chennai" "Commercial") 10000)
(= (base-rate-per-sqft "Chennai" "Land") 3000)

;; Multiplier Factors
(= (location-multiplier "Delhi" "Central") 1.5)
(= (location-multiplier "Delhi" "Suburban") 1.0)
(= (location-multiplier "Delhi" "Outer") 0.7)

(= (location-multiplier "Mumbai" "Central") 2.0)
(= (location-multiplier "Mumbai" "Suburban") 1.2)
(= (location-multiplier "Mumbai" "Outer") 0.8)

;; Age Factor
(= (age-factor ?year-built) 
    (if (< ?year-built 2020)
        (if (< ?year-built 2010)
            (if (< ?year-built 2000)
                0.7  ; Very old
                0.8) ; Old
            0.9)     ; Recent
        1.0))        ; New

;; Bedroom Factor
(= (bedroom-factor ?bedrooms) 
    (if (> ?bedrooms 3)
        1.2  ; Premium for 4+ bedrooms
        (if (= ?bedrooms 3)
            1.1  ; Good for 3 bedrooms
            (if (= ?bedrooms 2)
                1.0  ; Standard for 2 bedrooms
                0.9)))) ; Lower for 1 bedroom

;; Size Factor
(= (size-factor ?size) 
    (if (> ?size 2000)
        1.3  ; Large properties premium
        (if (> ?size 1500)
            1.1  ; Medium-large premium
            (if (> ?size 1000)
                1.0  ; Standard
                0.9)))) ; Smaller properties

;; Main Valuation Function
(= (calculate-valuation ?listing) 
    (let ((location (get-location ?listing))
          (property-type (get-property-type ?listing))
          (size (get-size ?listing))
          (bedrooms (get-bedrooms ?listing))
          (year-built (get-year-built ?listing))
          (area-type (get-area-type ?listing)))
        
        (let ((base-rate (base-rate-per-sqft ?location ?property-type))
              (loc-mult (location-multiplier ?location ?area-type))
              (age-fact (age-factor ?year-built))
              (bed-fact (bedroom-factor ?bedrooms))
              (size-fact (size-factor ?size)))
            
            (let ((base-value (* ?size ?base-rate))
                  (adjusted-value (* ?base-value ?loc-mult ?age-fact ?bed-fact ?size-fact))
                  (min-value (* ?adjusted-value 0.85))
                  (max-value (* ?adjusted-value 1.15)))
                
                (valuation-range ?min-value ?max-value)))))

;; Valuation Range Helper
(= (valuation-range ?min ?max) 
    (list "min" ?min "max" ?max "currency" "INR"))

;; Get Property Attributes
(= (get-location ?listing) (location ?listing))
(= (get-property-type ?listing) (property-type ?listing))
(= (get-size ?listing) (listing-size ?listing))
(= (get-bedrooms ?listing) (bedrooms ?listing))
(= (get-year-built ?listing) (year-built ?listing))
(= (get-area-type ?listing) (area-type ?listing))

;; Fuzzy Reasoning for Market Conditions
(= (market-condition-factor ?location) 
    (if (market-trend ?location "bullish")
        1.1
        (if (market-trend ?location "bearish")
            0.9
            1.0)))

;; Final Valuation with Market Conditions
(= (final-valuation ?listing) 
    (let ((base-valuation (calculate-valuation ?listing))
          (location (get-location ?listing))
          (market-factor (market-condition-factor ?location)))
        
        (let ((min-val (* (get-min-value ?base-valuation) ?market-factor))
              (max-val (* (get-max-value ?base-valuation) ?market-factor)))
            
            (valuation-range ?min-val ?max-val))))

;; Helper Functions
(= (get-min-value (list "min" ?min . ?rest)) ?min)
(= (get-max-value (list "max" ?max . ?rest)) ?max)

