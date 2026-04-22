"""Neo4j utility functions for AdvisorLens.

All queries against the Neo4j academicworld graph live here.
Widgets that use this module:
  4 (Network)       — professor collaboration graph
  6 (Universities)  — university research profile + compare
"""
from neo4j import GraphDatabase

# ── Connection ────────────────────────────────────────────────────────────────

NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "ilovecs411"

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


NEO4J_DB = "academicworld"


def _run(query, **params):
    """Run a read query and return list of record dicts."""
    with get_driver().session(database=NEO4J_DB) as session:
        result = session.run(query, **params)
        return [dict(r) for r in result]


# ── Widget 4 — Network (professor collaboration graph) ───────────────────────

def get_professor_network(professor_name, max_colleagues=10, max_keywords=8):
    """Return nodes and edges for a professor's collaboration network.

    Nodes:
      - The queried professor (type='faculty', highlighted)
      - Colleagues who share keywords (type='faculty')
      - Top keywords shared with colleagues (type='keyword')

    Edges:
      - faculty → keyword  (INTERESTED_IN)
      - faculty ← keyword  (keyword shared with colleague)

    Returns dict with keys:
        nodes — list of {id, label, type, data}
        edges — list of {source, target}
    """
    # Colleagues via shared keywords
    colleague_query = """
        MATCH (f:FACULTY {name: $name})-[:INTERESTED_IN]->(k:KEYWORD)<-[:INTERESTED_IN]-(c:FACULTY)
        WHERE c.name <> $name
        WITH c, collect(DISTINCT k.name) AS shared_kws, count(DISTINCT k) AS shared_count
        ORDER BY shared_count DESC
        LIMIT $limit
        RETURN c.name AS colleague, shared_kws, shared_count
    """
    colleagues = _run(colleague_query, name=professor_name, limit=max_colleagues)

    # Top keywords for the professor
    kw_query = """
        MATCH (f:FACULTY {name: $name})-[r:INTERESTED_IN]->(k:KEYWORD)
        RETURN k.name AS keyword, r.score AS score
        ORDER BY score DESC
        LIMIT $limit
    """
    keywords = _run(kw_query, name=professor_name, limit=max_keywords)

    # Build nodes & edges
    nodes = [{"id": professor_name, "label": professor_name, "type": "faculty_main"}]
    edges = []
    seen_nodes = {professor_name}

    for kw in keywords:
        kname = kw["keyword"]
        if kname not in seen_nodes:
            nodes.append({"id": kname, "label": kname, "type": "keyword"})
            seen_nodes.add(kname)
        edges.append({"source": professor_name, "target": kname})

    for col in colleagues:
        cname = col["colleague"]
        if cname not in seen_nodes:
            nodes.append({"id": cname, "label": cname, "type": "faculty"})
            seen_nodes.add(cname)
        for kname in col["shared_kws"][:3]:   # max 3 shared edges per colleague
            if kname in seen_nodes:
                edges.append({"source": cname, "target": kname})

    return {"nodes": nodes, "edges": edges}


def get_all_faculty_names_neo4j():
    """Return sorted list of faculty names from Neo4j (for network dropdown)."""
    rows = _run("MATCH (f:FACULTY) RETURN f.name AS name ORDER BY f.name")
    return [r["name"] for r in rows if r["name"]]


# ── Widget 6 — Universities (Neo4j side) ─────────────────────────────────────

def get_all_university_names_neo4j():
    """Return sorted list of university names from Neo4j."""
    rows = _run("MATCH (u:INSTITUTE) RETURN u.name AS name ORDER BY u.name")
    return [r["name"] for r in rows if r["name"]]


def get_university_top_keywords_neo4j(university_name, limit=5):
    """Return top keywords for a university via Neo4j graph traversal.

    Returns list of {keyword, total_score}.
    """
    query = """
        MATCH (u:INSTITUTE {name: $name})<-[:AFFILIATION_WITH]-(f:FACULTY)
              -[r:INTERESTED_IN]->(k:KEYWORD)
        WITH k.name AS keyword, sum(r.score) AS total_score
        ORDER BY total_score DESC
        LIMIT $limit
        RETURN keyword, total_score
    """
    return _run(query, name=university_name, limit=limit)


def get_university_faculty_count_neo4j(university_name):
    """Return number of faculty at a university."""
    rows = _run(
        "MATCH (u:INSTITUTE {name: $name})<-[:AFFILIATION_WITH]-(f:FACULTY) RETURN count(f) AS cnt",
        name=university_name,
    )
    return rows[0]["cnt"] if rows else 0


def get_university_compare_data(university_name):
    """Return comparison data for a university (used in Widget 6 compare modal).

    Returns dict with keys:
        name, faculty_count, top_keywords (list[str])
    """
    top_kws = get_university_top_keywords_neo4j(university_name, limit=5)
    faculty_count = get_university_faculty_count_neo4j(university_name)

    return {
        "name":          university_name,
        "faculty_count": faculty_count,
        "top_keywords":  [k["keyword"] for k in top_kws],
    }
