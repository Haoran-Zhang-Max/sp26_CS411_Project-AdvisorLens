"""MySQL utility functions for AdvisorLens.

All queries against the academicworld MySQL database live here.
Widgets that use this module: 1 (Find Advisor), 3 (Keyword Trends).

NOTE: pd.read_sql() does not work reliably with pymysql DictCursor.
      All SELECT queries use cursor.fetchall() → pd.DataFrame() instead.
"""
import pymysql
import pandas as pd

# ── Connection ────────────────────────────────────────────────────────────────

DB_CONFIG = dict(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="test_root",
    database="academicworld",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def _query(sql, params=None):
    """Execute a SELECT and return a pandas DataFrame."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
        return pd.DataFrame(rows)
    finally:
        conn.close()


# ── Schema helpers (run once on first use) ────────────────────────────────────

def setup_indexes():
    """Create performance indexes (R13 — Indexing technique).

    Checks existence via SHOW INDEX before creating to avoid duplicate-key errors
    on MySQL versions that don't support CREATE INDEX IF NOT EXISTS.
    """
    indexes = [
        ("faculty_keyword", "idx_fk_score",   "score"),
        ("publication",     "idx_pub_year",   "year"),
        ("faculty_keyword", "idx_fk_keyword", "keyword_id"),
    ]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for table, idx_name, column in indexes:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM information_schema.statistics "
                    "WHERE table_schema = %s AND table_name = %s AND index_name = %s",
                    ("academicworld", table, idx_name),
                )
                if cur.fetchone()["cnt"] == 0:
                    cur.execute(f"CREATE INDEX {idx_name} ON {table}({column});")
                    print(f"  Created index {idx_name} on {table}({column})")
                else:
                    print(f"  Index {idx_name} already exists — skipped")
        conn.commit()
    finally:
        conn.close()


def create_stored_procedure():
    """Create get_top_professors stored procedure (R14 — Stored Procedure technique)."""
    drop_sql = "DROP PROCEDURE IF EXISTS get_top_professors;"
    create_sql = """
    CREATE PROCEDURE get_top_professors(IN kw VARCHAR(255), IN lim INT)
    BEGIN
        SELECT f.id, f.name, f.position, u.name AS university,
               fk.score, COUNT(fp.publication_Id) AS pub_count
        FROM faculty f
        JOIN faculty_keyword fk  ON f.id = fk.faculty_id
        JOIN keyword k           ON fk.keyword_id = k.id
        JOIN university u        ON f.university_id = u.id
        LEFT JOIN faculty_publication fp ON f.id = fp.faculty_Id
        WHERE k.name LIKE CONCAT('%', kw, '%')
        GROUP BY f.id, f.name, f.position, u.name, fk.score
        ORDER BY fk.score DESC
        LIMIT lim;
    END
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(drop_sql)
            cur.execute(create_sql)
        conn.commit()
    finally:
        conn.close()


# ── Dropdown data ─────────────────────────────────────────────────────────────

def get_all_universities():
    """Return sorted list of university names for filter dropdowns."""
    df = _query("SELECT name FROM university ORDER BY name;")
    return df["name"].tolist()


def get_all_keywords():
    """Return sorted list of keyword names for search dropdowns."""
    df = _query("SELECT name FROM keyword ORDER BY name;")
    return df["name"].tolist()


def get_all_faculty_names():
    """Return sorted list of faculty names for filter dropdowns."""
    df = _query("SELECT name FROM faculty ORDER BY name;")
    return df["name"].tolist()


# ── Widget 1 — Find Advisor ───────────────────────────────────────────────────

def search_professors(keyword, sort_by="score", university=None, position=None):
    """Search professors by keyword with optional sort and filters.

    Args:
        keyword:    research keyword string (partial match)
        sort_by:    'score' | 'pub_count' | 'position'
        university: optional university name filter
        position:   optional position filter ('Professor' / 'Associate Professor' / etc.)

    Returns:
        pandas DataFrame with columns: id, name, position, university, score, pub_count
    """
    sort_map = {
        "score":     "fk.score DESC",
        "pub_count": "pub_count DESC",
        "position":  "f.position ASC",
    }
    order_clause = sort_map.get(sort_by, "fk.score DESC")

    sql = """
        SELECT f.id, f.name, f.position, u.name AS university,
               fk.score, COUNT(fp.publication_Id) AS pub_count
        FROM faculty f
        JOIN faculty_keyword fk  ON f.id = fk.faculty_id
        JOIN keyword k           ON fk.keyword_id = k.id
        JOIN university u        ON f.university_id = u.id
        LEFT JOIN faculty_publication fp ON f.id = fp.faculty_Id
        WHERE k.name LIKE %s
    """
    params = [f"%{keyword}%"]

    if university:
        sql += " AND u.name = %s"
        params.append(university)
    if position and position != "All":
        sql += " AND f.position = %s"
        params.append(position)

    sql += f" GROUP BY f.id, f.name, f.position, u.name, fk.score ORDER BY {order_clause};"

    return _query(sql, params)


def call_get_top_professors(keyword, limit=20):
    """Call the get_top_professors stored procedure (R14 technique).

    Returns pandas DataFrame identical to search_professors output.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.callproc("get_top_professors", (keyword, limit))
            rows = cur.fetchall()
        return pd.DataFrame(rows)
    finally:
        conn.close()


# ── Widget 3 — Keyword Trends ─────────────────────────────────────────────────

def get_keyword_trend(keyword, university=None, professor=None):
    """Publication count per year for a given keyword.

    Optional filters narrow results to a specific university or professor.

    Returns:
        pandas DataFrame with columns: year, pub_count
    """
    sql = """
        SELECT p.year, COUNT(DISTINCT p.ID) AS pub_count
        FROM publication p
        JOIN publication_keyword pk ON p.ID = pk.publication_id
        JOIN keyword k              ON pk.keyword_id = k.id
        JOIN faculty_publication fp ON p.ID = fp.publication_Id
        JOIN faculty f              ON fp.faculty_Id = f.id
        JOIN university u           ON f.university_id = u.id
        WHERE k.name LIKE %s
          AND p.year IS NOT NULL
    """
    params = [f"%{keyword}%"]

    if university:
        sql += " AND u.name = %s"
        params.append(university)
    if professor:
        sql += " AND f.name = %s"
        params.append(professor)

    sql += " GROUP BY p.year ORDER BY p.year ASC;"

    return _query(sql, params)


# ── Widget 6 — University stats (MySQL side) ──────────────────────────────────

def get_university_stats(university_name):
    """Return research stats for a university.

    Returns:
        dict with keys: pub_count (int), top_keywords (list[str]),
                        top_professors (DataFrame[name, total_citations])
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(DISTINCT fp.publication_Id) AS pub_count
                FROM faculty f
                JOIN faculty_publication fp ON f.id = fp.faculty_Id
                JOIN university u           ON f.university_id = u.id
                WHERE u.name = %s;
                """,
                (university_name,),
            )
            pub_count = (cur.fetchone() or {}).get("pub_count", 0)

            cur.execute(
                """
                SELECT k.name, SUM(fk.score) AS total_score
                FROM faculty f
                JOIN faculty_keyword fk ON f.id = fk.faculty_id
                JOIN keyword k          ON fk.keyword_id = k.id
                JOIN university u       ON f.university_id = u.id
                WHERE u.name = %s
                GROUP BY k.id, k.name
                ORDER BY total_score DESC
                LIMIT 5;
                """,
                (university_name,),
            )
            top_keywords = [r["name"] for r in cur.fetchall()]

            cur.execute(
                """
                SELECT f.name, SUM(p.num_citations) AS total_citations
                FROM faculty f
                JOIN faculty_publication fp ON f.id = fp.faculty_Id
                JOIN publication p          ON fp.publication_Id = p.ID
                JOIN university u           ON f.university_id = u.id
                WHERE u.name = %s
                GROUP BY f.id, f.name
                ORDER BY total_citations DESC
                LIMIT 5;
                """,
                (university_name,),
            )
            top_professors = pd.DataFrame(cur.fetchall())

        return {
            "pub_count": pub_count,
            "top_keywords": top_keywords,
            "top_professors": top_professors,
        }
    finally:
        conn.close()
