-- Institution Duplicate Cleanup Migration Part 2
-- Merges 48 NULL MCC institutions into their same-state MCC-coded duplicates
-- Generated from pattern matching analysis

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM neetcounselling2025.institution
        WHERE mcc_institute_code IS NULL
        AND institution_id IN (2097, 2098, 2102, 2104, 2113, 2115, 2119, 2121, 2123, 2131, 2136, 2137, 2141, 2145, 2146, 2152, 2155, 2157, 2158, 2164, 2165, 2166, 2168, 2170, 2172, 2173, 2174, 2184, 2185, 2186, 2189, 2192, 2214, 2216, 2217, 2222, 2226, 2227, 2246, 2278, 2280, 2284, 2288, 2292, 2294, 2300, 2302, 2305)
        LIMIT 1
    ) THEN
        RAISE NOTICE 'Part 2 migration already applied or NULL MCC institutions not found.';
        RETURN;
    END IF;
END $$;

BEGIN;

CREATE TEMP TABLE IF NOT EXISTS institution_merge_map_2 (
    valid_id bigint,
    dup_id bigint,
    institution_name text
);

TRUNCATE institution_merge_map_2;

INSERT INTO institution_merge_map_2 (valid_id, dup_id, institution_name) VALUES
(2101, 2278, 'AIIMS Mangalagiri, ALL INDIA INSTITUTE OF MEDICAL SCIENCES NEAR TADEPALLI MANGALAGIRI GUNTUR (Dt) ANDHRA PRADESH'),
(1907, 2172, 'GOVERNMENT MEDICAL COLLEGE NANDYAL'),
(1840, 2155, 'GOVT MEDICAL COLLEGE VIZIANAGARAM'),
(1891, 2166, 'RIMS Srikakulam'),
(1704, 2216, 'SVIMS - Sri Padmavathi Medical College for Women, Tirupati(Female Seat only )'),
(1555, 2104, 'AIIMS Guwahati'),
(1970, 2185, 'Kokrajhar Medical College & Hospital Rangalikhata'),
(2181, 2305, 'Nagaon Medical college, Dipholu'),
(1989, 2189, 'Government DentalCollege and Hospital Paithna Bhaganbigha Rahui Nalanda'),
(1845, 2158, 'GOVERNMENT MEDICAL COLLEGE PURNEA'),
(2013, 2222, 'College of Nursing Dr. RML Hospital, New Delhi(Female Seat only )'),
(1546, 2214, 'Lady Hardinge Medical College, New Delhi(Female Seat only )'),
(1533, 2098, 'AIIMS Rajkot'),
(2107, 2284, 'AIIMS Jammu, AIIMS'),
(1552, 2102, 'Bangalore Medical College and Research Institute'),
(1874, 2164, 'Chikkamagaluru Institute of Medical Sciences'),
(1911, 2174, 'Chitradurga Medical College and Research Institute'),
(1823, 2152, 'Gadag Institute of Medical Sciences'),
(1893, 2168, 'Koppal Institute of Medical Sciences'),
(1591, 2113, 'MYSORE MED.& RESEARCH INST. MYSORE'),
(1800, 2146, 'Chhindwara Institute of Medical Sciences'),
(2132, 2294, 'Government Medical College Satna, Near Kendriya Vidyalaya No. 2'),
(1844, 2157, 'Sundarlal patwa Govt medical College mandsaur'),
(1757, 2136, 'Goverment Medical College And Hospital Jalgaon'),
(1775, 2141, 'Rajarshee Chhatrapati Shahu Maharaj Government Medical College Kolhapur'),
(1849, 2217, 'SYMBIOSIS MEDICAL COLLEGE FOR WOMEN PUNE(Female Seat only )'),
(1596, 2115, 'JIPMER KARAIKAL'),
(1528, 2097, 'JIPMER PUDUCHERRY'),
(2105, 2280, 'AIIMS Bathinda, Jodhpur Romana near Giani Zail Singh College Mandi Dabwali Road Bathinda'),
(2004, 2192, 'GOVT DEN COLL DENTAL WING PATIALA'),
(1720, 2131, 'GMC DAUSA RAJASTHAN'),
(1788, 2145, 'GMC KARAULI'),
(2142, 2288, 'Government Medical College Chittorgarh, Government Medical College Chittorgarh Bojunda - Udaipur Road Chittorgarh'),
(1677, 2121, 'SHRI KALYAN GOVT MEDICAL COLLEGE SIKAR'),
(1975, 2186, 'Govt dental college Pudukkottai'),
(1760, 2137, 'Govt. Sivgangai M. C. Sivagangai'),
(1969, 2184, 'GMC Kamareddy'),
(1910, 2173, 'GOVERNMENT MEDICAL COLLEGE Karimnagar Telangana'),
(2182, 2302, 'Govt Medical College Vikarabad, ANANTHAGIRI HILLS VIKARABAD VIKARABAD DISTRICT TELANGANA 501101'),
(1663, 2119, 'Kakatiya Medical College Warangal'),
(2096, 2227, 'Malla Reddy Dental College For Women, Hyderabad(Female Seat only )'),
(2085, 2226, 'Malla Reddy Medical College for Women, Hyderabad(Female Seat only )'),
(1685, 2123, 'Rajiv Gandhi Institute Medical Sce of Adilabad'),
(2143, 2292, 'Govt Medical College Faizabad, GANJA PARGANA- HAVELI AWADH'),
(1897, 2170, 'Maharaja Jitendra Narayan Medical College and Hospital Coochbehar'),
(1886, 2165, 'Raiganj Government Medical College'),
(2169, 2246, 'RAMPURHAT GOVT MEDICAL COLLEGE RAMPURHAT, RAMPURHAT GOVERNMENT MEDICAL COLLEGE AND HOSPITAL PO RAMPURHAT PS RAMPURHAT PIN 731224 DIST'),
(2169, 2300, 'RAMPURHAT GOVT MEDICAL COLLEGE RAMPURHAT, RAMPURHAT GOVERNMENT MEDICAL COLLEGE AND HOSPITAL PO RAMPURHAT PS RAMPURHAT PIN 731224 DIST BIRBHUM');

UPDATE neetcounselling2025.round_cutoff rc
SET institution_id = m.valid_id
FROM institution_merge_map_2 m
WHERE rc.institution_id = m.dup_id;

UPDATE neetcounselling2025.allotment_raw_parsed ap
SET institute_id = m.valid_id
FROM institution_merge_map_2 m
WHERE ap.institute_id = m.dup_id;

UPDATE neetcounselling2025.allotment_result_effective are
SET institution_id = m.valid_id
FROM institution_merge_map_2 m
WHERE are.institution_id = m.dup_id;

UPDATE neetcounselling2025.final_seat_matrix_row fsm
SET institution_id = m.valid_id
FROM institution_merge_map_2 m
WHERE fsm.institution_id = m.dup_id;

INSERT INTO neetcounselling2025.institution_alias (institution_id, alias_raw, alias_normalized)
SELECT m.valid_id, a.alias_raw, a.alias_normalized
FROM institution_merge_map_2 m
JOIN neetcounselling2025.institution_alias a ON a.institution_id = m.dup_id
WHERE a.alias_raw NOT IN (
    SELECT alias_raw FROM neetcounselling2025.institution_alias WHERE institution_id = m.valid_id
)
ON CONFLICT DO NOTHING;

DELETE FROM neetcounselling2025.institution_alias a
WHERE EXISTS (
    SELECT 1 FROM institution_merge_map_2 m 
    WHERE a.institution_id = m.dup_id
);

DELETE FROM neetcounselling2025.institution i
WHERE EXISTS (
    SELECT 1 FROM institution_merge_map_2 m 
    WHERE i.institution_id = m.dup_id
);

SELECT 'Remaining NULL MCC with data' as check_name, COUNT(*) as cnt
FROM neetcounselling2025.institution i
WHERE i.mcc_institute_code IS NULL
  AND EXISTS (
      SELECT 1 FROM neetcounselling2025.round_cutoff rc 
      WHERE rc.institution_id = i.institution_id
  );

DROP TABLE IF EXISTS institution_merge_map_2;

COMMIT;
