-- Institution Duplicate Cleanup Migration
-- Staging result: 33 dups merged, 155 round_cutoff + 660 allotment rows moved, 0 remaining duplicates
-- This script is idempotent - safe to run multiple times

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM neetcounselling2025.institution
        WHERE mcc_institute_code IS NULL
        AND UPPER(REPLACE(institution_name, ' ', '')) IN (
            SELECT UPPER(REPLACE(institution_name, ' ', ''))
            FROM neetcounselling2025.institution
            WHERE mcc_institute_code IS NOT NULL
        )
        LIMIT 1
    ) THEN
        RAISE NOTICE 'No duplicate institutions found. Migration already applied or not needed.';
        RETURN;
    END IF;
END $$;

BEGIN;

CREATE TEMP TABLE IF NOT EXISTS institution_merge_map (
    valid_id bigint,
    dup_id bigint,
    institution_name text
);

TRUNCATE institution_merge_map;

INSERT INTO institution_merge_map (valid_id, dup_id, institution_name) VALUES
(1540, 2100, 'GOVT.MEDICAL COLLEGE, THIRUVANANTHAPURAM'),
(1540, 2213, 'GOVT.MEDICAL COLLEGE, THIRUVANANTHAPURAM'),
(1540, 2307, 'GOVT.MEDICAL COLLEGE, THIRUVANANTHAPURAM'),
(1555, 2281, 'AIIMS Guwahati'),
(1562, 2106, 'COIMBATORE MEDICAL COLLEGE'),
(1580, 2109, 'INST OF PG MED EDU'),
(1581, 2306, 'Gandhi Medical College'),
(1588, 2111, 'GOVT. MEDICAL COLLEGE, TIRUNELVELI'),
(1592, 2114, 'GOVT. MOHAN KUMARAMANGALAM'),
(1625, 2117, 'GOVT. MEDICAL COLLEGE, AURANGABAD'),
(1681, 2122, 'KANYAKUMARI GOVT. MED. COLL.'),
(1705, 2126, 'M.G.M. MEDICAL COLLEGE'),
(1712, 2128, 'NORTH BENGAL MED.COLL'),
(1717, 2130, 'THOOTHUKUDI MEDICAL COLLEGE'),
(1755, 2135, 'BURDWAN MEDICAL COLLEGE'),
(1772, 2139, 'SH VASANT RAO NAIK GOVT.M.C.'),
(1812, 2148, 'MAHARSHI DEVRAHA BABA'),
(1841, 2156, 'GOVT. DENTAL COLLEGE'),
(1845, 2296, 'GOVERNMENT MEDICAL COLLEGE PURNEA'),
(1845, 2310, 'GOVERNMENT MEDICAL COLLEGE PURNEA'),
(1857, 2160, 'AGARTALA GOVT. MEDICAL COLLEGE'),
(1879, 2309, 'Government Medical College Alibag'),
(1907, 2301, 'GOVERNMENT MEDICAL COLLEGE NANDYAL'),
(1907, 2311, 'GOVERNMENT MEDICAL COLLEGE NANDYAL'),
(1941, 2179, 'S.C.B. MEDICAL COLL(DENTAL)'),
(1970, 2312, 'Kokrajhar Medical College'),
(1997, 2190, 'NORTH BENGAL DENT.COLL'),
(1997, 2219, 'NORTH BENGAL DENT.COLL'),
(1997, 2313, 'NORTH BENGAL DENT.COLL'),
(2063, 2206, 'Jagadguru Gangadhar'),
(2063, 2225, 'Jagadguru Gangadhar'),
(2063, 2314, 'Jagadguru Gangadhar'),
(2228, 2282, 'ESIC MEDICAL COLLEGE');

UPDATE neetcounselling2025.round_cutoff rc
SET institution_id = m.valid_id
FROM institution_merge_map m
WHERE rc.institution_id = m.dup_id;

UPDATE neetcounselling2025.allotment_raw_parsed ap
SET institute_id = m.valid_id
FROM institution_merge_map m
WHERE ap.institute_id = m.dup_id;

UPDATE neetcounselling2025.allotment_result_effective are
SET institution_id = m.valid_id
FROM institution_merge_map m
WHERE are.institution_id = m.dup_id;

UPDATE neetcounselling2025.final_seat_matrix_row fsm
SET institution_id = m.valid_id
FROM institution_merge_map m
WHERE fsm.institution_id = m.dup_id;

INSERT INTO neetcounselling2025.institution_alias (institution_id, alias_raw, alias_normalized)
SELECT m.valid_id, a.alias_raw, a.alias_normalized
FROM institution_merge_map m
JOIN neetcounselling2025.institution_alias a ON a.institution_id = m.dup_id
WHERE a.alias_raw NOT IN (
    SELECT alias_raw FROM neetcounselling2025.institution_alias WHERE institution_id = m.valid_id
)
ON CONFLICT DO NOTHING;

DELETE FROM neetcounselling2025.institution_alias a
WHERE EXISTS (
    SELECT 1 FROM institution_merge_map m 
    WHERE a.institution_id = m.dup_id
);

DELETE FROM neetcounselling2025.institution i
WHERE EXISTS (
    SELECT 1 FROM institution_merge_map m 
    WHERE i.institution_id = m.dup_id
);

SELECT 'Remaining duplicates' as check_name, COUNT(*) as cnt
FROM neetcounselling2025.institution
WHERE mcc_institute_code IS NULL
  AND institution_id IN (
      SELECT MIN(institution_id) 
      FROM neetcounselling2025.institution 
      GROUP BY UPPER(REPLACE(institution_name, ' ', ''))
      HAVING COUNT(*) > 1
  );

DROP TABLE IF EXISTS institution_merge_map;

COMMIT;
