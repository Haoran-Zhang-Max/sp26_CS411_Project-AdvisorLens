# AdvisorLens

A web application that helps graduate students find and compare research advisors, built for CS411 Database Systems (Spring 2026).

---

## Purpose

**Application Scenario:**
Graduate students at research universities often struggle to identify faculty advisors whose research interests align with their own. AdvisorLens solves this by providing a unified dashboard that lets students search, explore, and compare professors across the Academic World dataset — covering thousands of faculty members, publications, and research keywords from universities worldwide.

**Target Users:**
- Graduate students looking for a research advisor or PhD supervisor
- Prospective PhD applicants researching faculty before applying
- Researchers exploring collaboration opportunities

**Objectives:**
- Allow users to search professors by research keyword and rank results by relevance, publication count, or position
- Provide rich professor profiles including publications, research keywords, and contact info
- Visualize how research topics have trended over time
- Show collaboration networks between professors via a graph interface
- Enable side-by-side comparison of professors (up to 4) and universities (up to 2)
- Let users save favorite professors and write personal notes with star ratings

---

## Demo

> 🎥 Video demo: [Watch on Illinois Media Space](https://mediaspace.illinois.edu/media/t/1_lsm0q0oi)

---

## Installation

### Prerequisites

- Python 3.9+
- MySQL running on `localhost:3306` with the `academicworld` database loaded
- MongoDB running on `localhost:27017` with the `academicworld` database loaded
- Neo4j running on `bolt://localhost:7687` with the `academicworld` database loaded

> You do not need to re-populate the databases — the Academic World dataset should already be loaded from your MP assignments.

### Install dependencies

```bash
pip install dash dash-bootstrap-components dash-cytoscape pymysql pymongo neo4j pandas cryptography
```

### Run

```bash
python app.py
```

Then open `http://127.0.0.1:8050` in your browser.

---

## Usage

AdvisorLens is organized into **7 tabs** across the top navigation bar. Here is how to use each one:

| Tab | What it does | How to use |
|-----|-------------|------------|
| **Find Advisor** | Search professors by keyword | Type a keyword, choose sort (relevance / publications / position) and optional filters, click a professor to open their profile |
| **Professor Profile** | View a full professor profile | Search or select a professor name; click "Add to Favorites" to save them |
| **Keyword Trends** | See how a research area has grown over time | Type a keyword; optionally filter by university or professor |
| **Network** | Explore a professor's collaboration graph | Select a professor; the graph shows connected professors and shared keywords |
| **Favorites** | View and compare saved professors | Select 2–4 professors via checkboxes, click "Compare" to open a side-by-side popup |
| **Universities** | Explore and compare university research profiles | Select a university to view its stats; check 2 universities and click "Compare" for a popup |
| **My Notes** | Save personal notes and ratings on professors | Pick a professor, write notes, set a star rating (1–5), click Save |

---

## Design

### Architecture

```
Browser (Dash frontend)
        │
        ▼
    app.py  ──── Tab routing + shared layout
        │
   components/
   ├── find_advisor.py
   ├── professor_profile.py
   ├── keyword_trends.py
   ├── network.py
   ├── favorites.py
   ├── universities.py
   └── my_notes.py
        │
     utils/
   ├── mysql_utils.py    ───►  MySQL (academicworld)
   ├── mongodb_utils.py  ───►  MongoDB (academicworld)
   └── neo4j_utils.py    ───►  Neo4j (academicworld)
```

### Key Design Decisions
- **Tab-based navigation** keeps each widget independent and easy to navigate
- **Popup modals** (via `dbc.Modal`) for professor and university comparison keep users in context without navigating away
- **Separation of concerns** — each component file owns its own layout and callbacks; utility files own all database logic
- **Each database is used where it fits best**: MySQL for relational filtering/sorting, MongoDB for rich document retrieval and user data, Neo4j for graph traversal

---

## Implementation

### Frameworks and Libraries

| Library | Purpose |
|---------|---------|
| `dash` | Core web framework — layout and callbacks |
| `dash-bootstrap-components` | UI components — modals, cards, grid layout |
| `dash-cytoscape` | Interactive graph visualization (Network tab) |
| `plotly` / `plotly.express` | Charts for Keyword Trends tab |
| `pandas` | Data wrangling for query results |
| `pymysql` | MySQL database access |
| `pymongo` | MongoDB database access |
| `neo4j` | Neo4j database access |

### How the Dashboard Works

Each tab is a separate Python file in `components/`. When a tab is selected, Dash renders its layout and registers its callbacks. Callbacks listen for user inputs (dropdown changes, button clicks, text input) and call the appropriate utility function to query the relevant database. Results are returned as Dash components (tables, charts, graphs, cards) rendered directly in the browser.

Popup modals (Favorites Compare, University Compare) are controlled by a boolean `is_open` state toggled by the Compare and Close buttons via Dash callbacks.

---

## Database Techniques

### 1. Indexing (MySQL) — satisfies R13

Three indexes are created on startup in `mysql_utils.py` to speed up the keyword search and trend queries used by Widgets 1 and 3:

```sql
CREATE INDEX IF NOT EXISTS idx_fk_score   ON faculty_keyword(score);
CREATE INDEX IF NOT EXISTS idx_pub_year   ON publication(year);
CREATE INDEX IF NOT EXISTS idx_fk_keyword ON faculty_keyword(keyword_id);
```

### 2. Stored Procedure (MySQL) — satisfies R14

A stored procedure `get_top_professors` is defined in MySQL and called by the Find Advisor tab for relevance-sorted searches. This encapsulates the multi-table join logic and improves maintainability:

```sql
DELIMITER //
CREATE PROCEDURE get_top_professors(IN kw VARCHAR(255), IN lim INT)
BEGIN
  SELECT f.name, f.position, u.name AS university, fk.score,
         COUNT(fp.publication_Id) AS pub_count
  FROM faculty f
  JOIN faculty_keyword fk ON f.id = fk.faculty_id
  JOIN keyword k           ON fk.keyword_id = k.id
  JOIN university u        ON f.university_id = u.id
  LEFT JOIN faculty_publication fp ON f.id = fp.faculty_Id
  WHERE k.name LIKE CONCAT('%', kw, '%')
  GROUP BY f.id
  ORDER BY fk.score DESC
  LIMIT lim;
END //
DELIMITER ;
```

### 3. Transaction (MongoDB) — satisfies R15

The Favorites tab uses a MongoDB client session with an explicit transaction when adding or removing a professor from the favorites collection. This ensures that reads and writes are atomic and consistent even if multiple operations are involved:

```python
with client.start_session() as session:
    with session.start_transaction():
        db.user_favorites.insert_one({...}, session=session)
```

---

## Extra-Credit Capabilities

*(None implemented in this submission — may be added before final deadline)*

---

## Contributions

| Member | Tasks Done | Time Spent |
|--------|-----------|------------|
| Haoran Zhang | Designed overall app concept and dashboard layout; built all 7 components (find_advisor, professor_profile, keyword_trends, network, favorites, universities, my_notes); implemented all three database utility files (mysql_utils, mongodb_utils, neo4j_utils); created database techniques (indexing, stored procedure, transaction); styled the UI with style.css; wrote README and recorded video demo | 60 hours |

---

## Project Structure

```
AdvisorLens/
├── app.py                        # Entry point, tab routing
├── assets/
│   └── style.css                 # Global styles
├── components/
│   ├── find_advisor.py           # Tab 1 — Find Advisor
│   ├── professor_profile.py      # Tab 2 — Professor Profile
│   ├── keyword_trends.py         # Tab 3 — Keyword Trends
│   ├── network.py                # Tab 4 — Network
│   ├── favorites.py              # Tab 5 — Favorites + Compare
│   ├── universities.py           # Tab 6 — Universities + Compare
│   └── my_notes.py               # Tab 7 — My Notes
└── utils/
    ├── mysql_utils.py            # MySQL connection + queries
    ├── mongodb_utils.py          # MongoDB connection + queries
    └── neo4j_utils.py            # Neo4j connection + queries
```
