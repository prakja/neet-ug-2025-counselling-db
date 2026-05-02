-- Fix Dr. B.R. Ambedkar State Institute - merge NULL MCC record into MCC-coded record with wrong state
BEGIN;

CREATE TEMP TABLE IF NOT EXISTS institution_merge_map_ambedkar (
    valid_id bigint,
    dup_id bigint,
    institution_name text
);

TRUNCATE institution_merge_map_ambedkar;

-- 2285 (NULL MCC, correct state Punjab) -> 2116 (MCC 200572, wrong state Jharkhand)
INSERT INTO institution_merge_map_ambedkar (valid_id, dup_id, institution_name) VALUES
(2116, 2285, 'Dr. B.R. Ambedkar State Institute of Medical Sciences, Sector 56 Mohali');

-- Update valid record state to correct value
UPDATE neetcounselling2025.institution
SET state_name = 'Punjab'
WHERE institution_id = 2116;

-- Migrate FK data from duplicate to valid
UPDATE neetcounselling2025.round_cutoff rc
SET institution_id = m.valid_id
FROM institution_merge_map_ambedkar m
WHERE rc.institution_id = m.dup_id;

UPDATE neetcounselling2025.allotment_raw_parsed ap
SET institute_id = m.valid_id
FROM institution_merge_map_ambedkar m
WHERE ap.institute_id = m.dup_id;

UPDATE neetcounselling2025.allotment_result_effective are
SET institution_id = m.valid_id
FROM institution_merge_map_ambedkar m
WHERE are.institution_id = m.dup_id;

UPDATE neetcounselling2025.final_seat_matrix_row fsm
SET institution_id = m.valid_id
FROM institution_merge_map_ambedkar m
WHERE fsm.institution_id = m.dup_id;

-- Migrate unique aliases
INSERT INTO neetcounselling2025.institution_alias (institution_id, alias_raw, alias_normalized)
SELECT m.valid_id, a.alias_raw, a.alias_normalized
FROM institution_merge_map_ambedkar m
JOIN neetcounselling2025.institution_alias a ON a.institution_id = m.dup_id
WHERE a.alias_raw NOT IN (
    SELECT alias_raw FROM neetcounselling2025.institution_alias WHERE institution_id = m.valid_id
)
ON CONFLICT DO NOTHING;

-- Delete duplicate aliases and institution
DELETE FROM neetcounselling2025.institution_alias a
WHERE EXISTS (SELECT 1 FROM institution_merge_map_ambedkar m WHERE a.institution_id = m.dup_id);

DELETE FROM neetcounselling2025.institution i
WHERE EXISTS (SELECT 1 FROM institution_merge_map_ambedkar m WHERE i.institution_id = m.dup_id);

-- Verify
SELECT institution_id, institution_name, state_name, mcc_institute_code
FROM neetcounselling2025.institution
WHERE institution_id = 2116;

SELECT 'Remaining NULL MCC with data' as check_name, COUNT(*) as cnt
FROM neetcounselling2025.institution i
WHERE i.mcc_institute_code IS NULL
  AND EXISTS (SELECT 1 FROM neetcounselling2025.round_cutoff rc WHERE rc.institution_id = i.institution_id);

DROP TABLE IF EXISTS institution_merge_map_ambedkar;

COMMIT;
