;; Recommendation Agent - MeTTa Rules
;; Purpose: Suggest properties to buyers based on history, preferences, and similarity

;; User Preference Extraction
(= (user-preferences ?user) 
    (let ((viewed-properties (viewed-properties ?user))
          (purchased-properties (purchased-properties ?user))
          (favorited-properties (favorited-properties ?user)))
        
        (preference-profile 
            (preferred-locations (extract-locations ?viewed-properties ?purchased-properties ?favorited-properties))
            (preferred-types (extract-property-types ?viewed-properties ?purchased-properties ?favorited-properties))
            (preferred-price-range (extract-price-range ?viewed-properties ?purchased-properties ?favorited-properties))
            (preferred-size-range (extract-size-range ?viewed-properties ?purchased-properties ?favorited-properties)))))

;; Location Similarity
(= (location-similarity ?loc1 ?loc2) 
    (if (= ?loc1 ?loc2)
        1.0  ; Exact match
        (if (same-city ?loc1 ?loc2)
            0.8  ; Same city
            (if (same-region ?loc1 ?loc2)
                0.6  ; Same region
                0.3)))) ; Different region

;; Property Type Similarity
(= (type-similarity ?type1 ?type2) 
    (if (= ?type1 ?type2)
        1.0  ; Exact match
        (if (compatible-types ?type1 ?type2)
            0.7  ; Compatible types
            0.2))) ; Incompatible types

;; Price Range Similarity
(= (price-similarity ?price1 ?price2 ?tolerance) 
    (let ((diff (abs (- ?price1 ?price2)))
          (avg-price (/ (+ ?price1 ?price2) 2)))
        (if (< ?diff (* ?avg-price ?tolerance))
            (- 1.0 (/ ?diff (* ?avg-price ?tolerance)))
            0.0)))

;; Size Similarity
(= (size-similarity ?size1 ?size2 ?tolerance) 
    (let ((diff (abs (- ?size1 ?size2)))
          (avg-size (/ (+ ?size1 ?size2) 2)))
        (if (< ?diff (* ?avg-size ?tolerance))
            (- 1.0 (/ ?diff (* ?avg-size ?tolerance)))
            0.0)))

;; Overall Similarity Score
(= (similarity-score ?listing1 ?listing2) 
    (let ((loc-sim (location-similarity (location ?listing1) (location ?listing2)))
          (type-sim (type-similarity (property-type ?listing1) (property-type ?listing2)))
          (price-sim (price-similarity (price ?listing1) (price ?listing2) 0.2))
          (size-sim (size-similarity (size ?listing1) (size ?listing2) 0.3)))
        
        (weighted-average 
            (list (weighted-score ?loc-sim 0.3)
                  (weighted-score ?type-sim 0.3)
                  (weighted-score ?price-sim 0.2)
                  (weighted-score ?size-sim 0.2)))))

;; Weighted Score Helper
(= (weighted-score ?score ?weight) (* ?score ?weight))

;; Weighted Average Helper
(= (weighted-average ?scores) 
    (let ((total-weight (sum-weights ?scores))
          (total-score (sum-scores ?scores)))
        (/ ?total-score ?total-weight)))

;; Collaborative Filtering
(= (collaborative-recommendation ?user ?listing) 
    (let ((similar-users (find-similar-users ?user))
          (user-ratings (get-user-ratings ?similar-users ?listing)))
        (average-rating ?user-ratings)))

;; Find Similar Users
(= (find-similar-users ?user) 
    (let ((user-preferences (user-preferences ?user))
          (all-users (all-users)))
        (filter-users-by-similarity ?all-users ?user-preferences 0.7)))

;; Content-Based Filtering
(= (content-based-recommendation ?user ?listing) 
    (let ((user-preferences (user-preferences ?user))
          (listing-attributes (listing-attributes ?listing)))
        (match-score ?user-preferences ?listing-attributes)))

;; Hybrid Recommendation
(= (hybrid-recommendation ?user ?listing) 
    (let ((collab-score (collaborative-recommendation ?user ?listing))
          (content-score (content-based-recommendation ?user ?listing)))
        (weighted-average 
            (list (weighted-score ?collab-score 0.4)
                  (weighted-score ?content-score 0.6)))))

;; Main Recommendation Function
(= (recommend-properties ?user ?limit) 
    (let ((user-preferences (user-preferences ?user))
          (all-listings (available-listings))
          (scored-listings (score-listings ?all-listings ?user)))
        (take-top ?scored-listings ?limit)))

;; Score Listings for User
(= (score-listings ?listings ?user) 
    (map (lambda (?listing) 
            (list ?listing (hybrid-recommendation ?user ?listing))) 
         ?listings))

;; Take Top N Results
(= (take-top ?scored-listings ?n) 
    (let ((sorted (sort-by-score ?scored-listings)))
        (take ?sorted ?n)))

;; Sort by Score (descending)
(= (sort-by-score ?scored-listings) 
    (sort ?scored-listings (lambda (?a ?b) (> (score ?a) (score ?b)))))

;; Extract User Preferences
(= (extract-locations ?viewed ?purchased ?favorited) 
    (unique (append (map location ?viewed) 
                    (map location ?purchased) 
                    (map location ?favorited))))

(= (extract-property-types ?viewed ?purchased ?favorited) 
    (unique (append (map property-type ?viewed) 
                    (map property-type ?purchased) 
                    (map property-type ?favorited))))

(= (extract-price-range ?viewed ?purchased ?favorited) 
    (let ((all-prices (append (map price ?viewed) 
                              (map price ?purchased) 
                              (map price ?favorited))))
        (price-range (min ?all-prices) (max ?all-prices))))

(= (extract-size-range ?viewed ?purchased ?favorited) 
    (let ((all-sizes (append (map size ?viewed) 
                             (map size ?purchased) 
                             (map size ?favorited))))
        (size-range (min ?all-sizes) (max ?all-sizes))))

;; Helper Functions
(= (score (list ?listing ?score)) ?score)
(= (unique ?list) (remove-duplicates ?list))
(= (take ?list ?n) (slice ?list 0 ?n))

