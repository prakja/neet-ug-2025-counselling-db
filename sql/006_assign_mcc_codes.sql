-- Institution MCC Code Update Migration
-- Assigns missing MCC codes to 2 legitimate institutions
-- ESIC Andheri: 904357
-- Dr. B.R. Ambedkar Mohali: 200572

BEGIN;

UPDATE neetcounselling2025.institution
SET mcc_institute_code = 904357
WHERE institution_id = 2287
  AND mcc_institute_code IS NULL;

SELECT 
    institution_id,
    institution_name,
    state_name,
    mcc_institute_code
FROM neetcounselling2025.institution
WHERE institution_id IN (2287, 2285);

COMMIT;
