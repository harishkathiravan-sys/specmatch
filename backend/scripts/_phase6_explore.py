"""Phase 6 exploration script — inspect V0.3 data."""
import sqlite3

conn = sqlite3.connect(r"d:\testing2\backend\specmatch.db")
cur = conn.cursor()

def q(sql):
    cur.execute(sql)
    return cur.fetchall()

print("--- lifecycle_events sample ---")
for r in q("SELECT entity_id,event_type,event_date,validation_status,authority_level FROM lifecycle_events LIMIT 5"):
    print(r)

print("--- qco sample ---")
for r in q("SELECT is_number,product,mandatory_status,effective_date,validation_status FROM qco LIMIT 5"):
    print(r)

print("--- hard_negatives sample ---")
for r in q("SELECT negative_standard_number,negative_title,negative_reason,similarity_score FROM hard_negatives LIMIT 3"):
    print(r)

print("--- regional_variants sample ---")
for r in q("SELECT standard_number,target_language,variant_text FROM regional_variants LIMIT 3"):
    print(r)

print("--- gold_labels sample ---")
for r in q("SELECT query_id,standard_id,label,relevance,validation_status FROM gold_labels LIMIT 5"):
    print(r)

print("--- benchmarks sample ---")
for r in q("SELECT query_id,query,expected_standard_ids,difficulty,source_type FROM benchmarks LIMIT 3"):
    print(r)

print("--- certification sample ---")
for r in q("SELECT is_number,certification_status,scheme FROM certification LIMIT 3"):
    print(r)

print("--- IS19763 ---")
for r in q("SELECT standard_number,title,current_status,record_type,synthetic_flag FROM standards WHERE standard_number LIKE 'IS 19763%'"):
    print(r)

print("--- standards count ---")
print(q("SELECT COUNT(*) FROM standards"))

print("--- current_status distribution ---")
for r in q("SELECT current_status, COUNT(*) FROM standards GROUP BY current_status ORDER BY 2 DESC LIMIT 10"):
    print(r)

print("--- query_expansions sample ---")
for r in q("SELECT standard_number,expanded_query,language FROM query_expansions LIMIT 3"):
    print(r)

print("--- evidence_spans sample ---")
for r in q("SELECT standard_number,field,evidence_text FROM evidence_spans LIMIT 3"):
    print(r)