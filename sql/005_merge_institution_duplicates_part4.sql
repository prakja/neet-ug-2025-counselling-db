-- Institution Duplicate Cleanup Migration Part 4
-- Merges 2 newly found NULL MCC institutions into their same-state MCC-coded duplicates
-- Discovered via relaxed similarity search

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM neetcounselling2025.institution
        WHERE institution_id IN (2299, 2297)
        LIMIT 1
    ) THEN
        RAISE NOTICE 'Part 4 migration already applied or institutions not found.';
        RETURN;
    END IF;
END $$;

BEGIN;

CREATE TEMP TABLE IF NOT EXISTS institution_merge_map_4 (
    valid_id bigint,
    dup_id bigint,
    institution_name text
);

TRUNCATE institution_merge_map_4;

INSERT INTO institution_merge_map_4 (valid_id, dup_id, institution_name) VALUES
(2176, 2299, 'GMC Jangaon, gmc.jangaon@gmail. com'),
(2180, 2297, 'GOVERNMENT MEDICAL COLLEGE MACHILIPATNAM, KARA AGRAHARAM NEAR RADAR STATION MACHILIPATNAM');

UPDATE neetcounselling2025.round_cutoff rc
SET institution_id = m.valid_id
FROM institution_merge_map_4 m
WHERE rc.institution_id = m.dup_id;

UPDATE neetcounselling2025.allotment_raw_parsed ap
SET institute_id = m.valid_id
FROM institution_merge_map_4 m
WHERE ap.institute_id = m.dup_id;

UPDATE neetcounselling2025.allotment_result_effective are
SET institution_id = m.valid_id
FROM institution_merge_map_4 m
WHERE are.institution_id = m.dup_id;

UPDATE neetcounselling2025.final_seat_matrix_row fsm
SET institution_id = m.valid_id
FROM institution_merge_map_4 m
WHERE fsm.institution_id = m.dup_id;

INSERT INTO neetcounselling2025.institution_alias (institution_id, alias_raw, alias_normalized)
SELECT m.valid_id, a.alias_raw, a.alias_normalized
FROM institution_merge_map_4 m
JOIN neetcounselling2025.institution_alias a ON a.institution_id = m.dup_id
WHERE a.alias_raw NOT IN (
    SELECT alias_raw FROM neetcounselling2025.institution_alias WHERE institution_id = m.valid_id
)
ON CONFLICT DO NOTHING;

DELETE FROM neetcounselling2025.institution_alias a
WHERE EXISTS (
    SELECT 1 FROM institution_merge_map_4 m 
    WHERE a.institution_id = m.dup_id
);

DELETE FROM neetcounselling2025.institution i
WHERE EXISTS (
    SELECT 1 FROM institution_merge_map_4 m 
    WHERE i.institution_id = m.dup_id
);

SELECT 'Remaining NULL MCC with data' as check_name, COUNT(*) as cnt
FROM neetcounselling2025.institution i
WHERE i.mcc_institute_code IS NULL
  AND EXISTS (
      SELECT 1 FROM neetcounselling2025.round_cutoff rc 
      WHERE rc.institution_id = i.institution_id
  );

DROP TABLE IF EXISTS institution_merge_map_4;

COMMIT;
