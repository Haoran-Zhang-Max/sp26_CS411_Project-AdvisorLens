"""MongoDB utility functions for AdvisorLens.

All queries/writes against the academicworld MongoDB database live here.
Widgets that use this module:
  2 (Professor Profile)  — read faculty + publications
  5 (Favorites)          — read/write user_favorites  (transaction R15)
  7 (My Notes)           — read/write user_notes

Schema (academicworld db):
  faculty      — {id, name, position, researchInterest, email, phone,
                   photoUrl, affiliation:{id,name,photoUrl},
                   keywords:[{id,name,score}], publications:[pub_id,...]}
  publications — {id, title, venue, year, numCitations, keywords:[...]}
  user_favorites (created by app) — {name, position, university, photoUrl,
                                      pub_count, top_keywords:[str]}
  user_notes    (created by app)  — {professor_name, rating, note, updated_at}
"""
from datetime import datetime, timezone
import pymongo
from pymongo import MongoClient

# ── Connection ────────────────────────────────────────────────────────────────

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME   = "academicworld"

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db():
    return get_client()[DB_NAME]


# ── Widget 2 — Professor Profile ──────────────────────────────────────────────

def get_all_faculty_names():
    """Return sorted list of all faculty names (for search dropdown)."""
    db = get_db()
    names = db.faculty.distinct("name")
    return sorted(names)


def get_professor_profile(name):
    """Fetch full profile for a professor.

    Returns dict with keys:
        id, name, position, university, university_photo, email, phone,
        photo_url, research_interest,
        keywords  — list of {name, score} sorted by score desc (top 10)
        publications — list of {title, year, venue, num_citations}
                       sorted by num_citations desc (top 10)
    Returns None if not found.
    """
    db = get_db()
    doc = db.faculty.find_one({"name": name})
    if not doc:
        return None

    # Resolve publication IDs → full publication documents (top 10 by citations)
    pub_ids = doc.get("publications", [])
    pub_docs = []
    if pub_ids:
        raw = list(
            db.publications.find(
                {"id": {"$in": pub_ids}},
                {"_id": 0, "title": 1, "year": 1, "venue": 1, "numCitations": 1},
            ).sort("numCitations", pymongo.DESCENDING).limit(10)
        )
        pub_docs = [
            {
                "title":         p.get("title", ""),
                "year":          p.get("year", ""),
                "venue":         p.get("venue", ""),
                "num_citations": p.get("numCitations", 0),
            }
            for p in raw
        ]

    # Keywords sorted by score, top 10
    kw_docs = sorted(doc.get("keywords", []), key=lambda k: k.get("score", 0), reverse=True)[:10]
    keywords = [{"name": k["name"], "score": round(k["score"], 2)} for k in kw_docs]

    affiliation = doc.get("affiliation") or {}

    return {
        "id":               doc.get("id"),
        "name":             doc.get("name", ""),
        "position":         doc.get("position", ""),
        "university":       affiliation.get("name", ""),
        "university_photo": affiliation.get("photoUrl", ""),
        "email":            doc.get("email", ""),
        "phone":            doc.get("phone", ""),
        "photo_url":        doc.get("photoUrl", ""),
        "research_interest": doc.get("researchInterest", ""),
        "keywords":         keywords,
        "publications":     pub_docs,
        "pub_count":        len(pub_ids),
        "top_keywords":     [k["name"] for k in keywords[:3]],
    }


# ── Widget 5 — Favorites ──────────────────────────────────────────────────────

def get_favorites():
    """Return list of saved favorite professors.

    Returns list of dicts with keys:
        name, position, university, photo_url, pub_count, top_keywords
    """
    db = get_db()
    docs = list(db.user_favorites.find({}, {"_id": 0}))
    return docs


def add_to_favorites(professor_name):
    """Save a professor to favorites. Uses a MongoDB session transaction (R15).

    Fetches fresh profile data from the faculty collection, then inserts
    into user_favorites (upsert by name to avoid duplicates).

    Returns True on success, False if professor not found.
    """
    profile = get_professor_profile(professor_name)
    if not profile:
        return False

    record = {
        "name":         profile["name"],
        "position":     profile["position"],
        "university":   profile["university"],
        "photo_url":    profile["photo_url"],
        "pub_count":    profile["pub_count"],
        "top_keywords": profile["top_keywords"],
    }

    client = get_client()
    db = client[DB_NAME]

    try:
        # Use a session transaction (R15 — Transaction technique)
        with client.start_session() as session:
            with session.start_transaction():
                db.user_favorites.update_one(
                    {"name": professor_name},
                    {"$set": record},
                    upsert=True,
                    session=session,
                )
    except pymongo.errors.OperationFailure:
        # Transactions require a replica set; fall back to non-transactional
        # (acceptable in dev; production should run a replica set)
        db.user_favorites.update_one(
            {"name": professor_name},
            {"$set": record},
            upsert=True,
        )

    return True


def remove_from_favorites(professor_name):
    """Remove a professor from favorites. Uses a MongoDB session transaction (R15).

    Returns True if a document was deleted, False if it wasn't found.
    """
    client = get_client()
    db = client[DB_NAME]

    try:
        with client.start_session() as session:
            with session.start_transaction():
                result = db.user_favorites.delete_one(
                    {"name": professor_name},
                    session=session,
                )
    except pymongo.errors.OperationFailure:
        result = db.user_favorites.delete_one({"name": professor_name})

    return result.deleted_count > 0


def is_favorite(professor_name):
    """Return True if the professor is already in favorites."""
    db = get_db()
    return db.user_favorites.count_documents({"name": professor_name}) > 0


# ── Widget 7 — My Notes ───────────────────────────────────────────────────────

def get_all_notes():
    """Return all saved notes, sorted by professor name.

    Returns list of dicts: {professor_name, rating, note, updated_at}
    """
    db = get_db()
    return list(db.user_notes.find({}, {"_id": 0}).sort("professor_name", 1))


def save_note(professor_name, rating, note_text):
    """Upsert a note for a professor.

    Args:
        professor_name: str
        rating:         int 1–5
        note_text:      str
    """
    db = get_db()
    db.user_notes.update_one(
        {"professor_name": professor_name},
        {
            "$set": {
                "professor_name": professor_name,
                "rating":         int(rating),
                "note":           note_text,
                "updated_at":     datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


def delete_note(professor_name):
    """Delete the note for a professor.

    Returns True if deleted, False if not found.
    """
    db = get_db()
    result = db.user_notes.delete_one({"professor_name": professor_name})
    return result.deleted_count > 0


def get_note(professor_name):
    """Return a single note dict (or None) for the given professor."""
    db = get_db()
    doc = db.user_notes.find_one({"professor_name": professor_name}, {"_id": 0})
    return doc
