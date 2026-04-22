"""Widget 6 — Universities + Compare (Tab 6)
Database: Neo4j (top keywords, faculty count) + MySQL (pub count, top professors)
Type: Querying widget (R11)

Single university profile view + side-by-side compare modal for exactly 2 universities.
"""
from dash import html, dcc, Input, Output, State, no_update, ctx, ALL
import dash_bootstrap_components as dbc

from utils.neo4j_utils import get_university_compare_data, get_all_university_names_neo4j
from utils.mysql_utils  import get_university_stats

# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    universities = get_all_university_names_neo4j()
    uni_options  = [{"label": u, "value": u} for u in universities if u and u.strip()]

    return html.Div([
        html.H2("Universities", className="widget-title"),

        # ── Single university profile ──────────────────────────────────────────
        html.Div([
            html.Div([
                html.Label("Select a University", className="control-label"),
                dcc.Dropdown(
                    id="uni-dropdown",
                    options=uni_options,
                    placeholder="Search for a university…",
                    clearable=True,
                    searchable=True,
                    className="control-dropdown",
                    style={"minWidth": "320px"},
                ),
            ], className="control-group control-group--wide"),
        ], className="controls-row"),

        html.Div(
            id="uni-profile-area",
            children=html.P("Select a university above to view its research profile.",
                            className="placeholder"),
        ),

        html.Hr(style={"margin": "28px 0 20px"}),

        # ── Compare section ────────────────────────────────────────────────────
        html.Div([
            html.H3("Compare Universities", style={
                "fontSize": "1rem", "fontWeight": "600",
                "color": "#1a3a5c", "marginBottom": "12px",
            }),
            html.P("Select 2–4 universities to compare side by side.",
                   className="table-hint", style={"marginBottom": "12px"}),

            html.Div([
                # Scrollable checklist
                html.Div(
                    dcc.Checklist(
                        id="uni-checklist",
                        options=uni_options,
                        value=[],
                        className="uni-checklist",
                        inputStyle={"marginRight": "8px", "accentColor": "#2e6da4"},
                        labelStyle={"display": "block", "padding": "5px 8px",
                                    "fontSize": "0.85rem", "cursor": "pointer",
                                    "borderRadius": "4px"},
                    ),
                    className="uni-checklist-scroll",
                ),

                # Right: selection status + button
                html.Div([
                    html.Div(id="uni-check-status", className="result-count",
                             style={"marginBottom": "12px"}),
                    html.Button(
                        "Compare",
                        id="uni-compare-btn",
                        n_clicks=0,
                        className="btn-primary",
                        disabled=True,
                    ),
                ], style={"display": "flex", "flexDirection": "column",
                          "justifyContent": "flex-start", "paddingTop": "4px"}),
            ], style={"display": "flex", "gap": "24px", "alignItems": "flex-start"}),
        ]),

        # ── Compare modal ─────────────────────────────────────────────────────
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("University Comparison")),
            dbc.ModalBody(html.Div(id="uni-modal-content")),
            dbc.ModalFooter(
                html.Button("Close", id="uni-modal-close", n_clicks=0,
                            className="btn-secondary")
            ),
        ], id="uni-compare-modal", is_open=False, size="xl", scrollable=True),

    ], className="widget-container")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _profile_card(name):
    """Build the single-university profile using Neo4j + MySQL data."""
    try:
        neo4j_data = get_university_compare_data(name)
        mysql_data = get_university_stats(name)
    except Exception as e:
        return html.P(f"Error loading data: {e}", className="placeholder")

    top_keywords   = neo4j_data.get("top_keywords", [])
    faculty_count  = neo4j_data.get("faculty_count", 0)
    pub_count      = mysql_data.get("pub_count", 0)
    top_professors = mysql_data.get("top_professors")

    kw_badges = [html.Span(kw, className="kw-badge") for kw in top_keywords]

    # Top professors table
    if top_professors is not None and not top_professors.empty:
        prof_rows = []
        for _, row in top_professors.iterrows():
            prof_rows.append(html.Tr([
                html.Td(row.get("name", ""), style={"padding": "6px 12px", "fontSize": "0.85rem"}),
                html.Td(
                    f'{int(row.get("total_citations", 0)):,}',
                    style={"padding": "6px 12px", "fontSize": "0.85rem",
                           "textAlign": "right", "color": "#2e6da4", "fontWeight": "600"},
                ),
            ]))
        prof_table = html.Table([
            html.Thead(html.Tr([
                html.Th("Professor", style={"padding": "8px 12px", "fontSize": "0.8rem",
                                            "color": "#fff", "background": "#1a3a5c"}),
                html.Th("Citations",  style={"padding": "8px 12px", "fontSize": "0.8rem",
                                             "color": "#fff", "background": "#1a3a5c",
                                             "textAlign": "right"}),
            ])),
            html.Tbody(prof_rows),
        ], style={"width": "100%", "borderCollapse": "collapse",
                  "border": "1px solid #e8ecf0", "borderRadius": "4px"})
    else:
        prof_table = html.P("No citation data available.", style={"color": "#888", "fontSize": "0.85rem"})

    return html.Div([
        # Stats row
        html.Div([
            _stat_chip(str(faculty_count), "Faculty"),
            _stat_chip(f"{pub_count:,}",   "Publications"),
            _stat_chip(str(len(top_keywords)), "Top Keywords"),
        ], className="uni-stats-row"),

        # Two columns: keywords | top professors
        html.Div([
            html.Div([
                html.H4("Top Research Keywords", className="section-subtitle"),
                html.Div(kw_badges, className="kw-badge-list"),
            ], style={"flex": "1", "minWidth": "200px"}),

            html.Div([
                html.H4("Most Cited Professors", className="section-subtitle"),
                prof_table,
            ], style={"flex": "1", "minWidth": "240px"}),
        ], style={"display": "flex", "gap": "32px", "flexWrap": "wrap", "marginTop": "16px"}),
    ], className="uni-profile-card")


def _stat_chip(value, label):
    return html.Div([
        html.Span(value, className="stat-value"),
        html.Span(label, className="stat-label"),
    ], className="stat-chip")


def _compare_uni_card(name):
    """Compact card for the comparison modal."""
    try:
        neo4j_data = get_university_compare_data(name)
        mysql_data = get_university_stats(name)
    except Exception:
        return html.Div(html.P(f"Error loading {name}"), className="compare-card")

    top_keywords  = neo4j_data.get("top_keywords", [])
    faculty_count = neo4j_data.get("faculty_count", 0)
    pub_count     = mysql_data.get("pub_count", 0)
    top_profs     = mysql_data.get("top_professors")
    top_prof_name = ""
    if top_profs is not None and not top_profs.empty:
        top_prof_name = top_profs.iloc[0].get("name", "")

    return html.Div([
        html.H5(name, className="compare-name",
                style={"fontSize": "0.92rem", "marginBottom": "10px"}),
        html.Hr(style={"margin": "6px 0"}),
        html.Div([
            _stat_chip(str(faculty_count), "Faculty"),
            _stat_chip(f"{pub_count:,}",   "Pubs"),
        ], className="uni-stats-row", style={"justifyContent": "center", "gap": "10px"}),
        html.Div([
            html.P("Top Keywords", style={"fontWeight": "600", "fontSize": "0.8rem",
                                          "color": "#555", "margin": "10px 0 4px"}),
            html.Div([html.Span(kw, className="kw-badge-sm") for kw in top_keywords],
                     className="kw-badge-list", style={"justifyContent": "center"}),
        ]),
        html.P([html.Strong("Top Professor: "), top_prof_name or "—"],
               style={"fontSize": "0.82rem", "color": "#555", "marginTop": "10px"}),
    ], className="compare-card", style={"flex": "1 1 260px", "maxWidth": "360px"})


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # 1. Single university profile
    @app.callback(
        Output("uni-profile-area", "children"),
        Input("uni-dropdown", "value"),
        prevent_initial_call=True,
    )
    def load_profile(name):
        if not name:
            return html.P("Select a university above to view its research profile.",
                          className="placeholder")
        return _profile_card(name)

    # 2. Update compare button state + status text
    @app.callback(
        Output("uni-compare-btn",  "disabled"),
        Output("uni-check-status", "children"),
        Input("uni-checklist", "value"),
        prevent_initial_call=True,
    )
    def update_compare_btn(selected):
        n = len(selected or [])
        if n == 0:
            return True, "No universities selected."
        if n == 1:
            return True, "Select 1 more university to compare."
        if 2 <= n <= 4:
            return False, f'{n} selected — ready to compare.'
        # n > 4: enforce max 4
        return True, f"{n} selected — please select at most 4."

    # 3. Open/close compare modal
    @app.callback(
        Output("uni-compare-modal", "is_open"),
        Output("uni-modal-content", "children"),
        Input("uni-compare-btn",  "n_clicks"),
        Input("uni-modal-close",  "n_clicks"),
        State("uni-checklist",    "value"),
        State("uni-compare-modal","is_open"),
        prevent_initial_call=True,
    )
    def toggle_modal(compare_clicks, close_clicks, selected, is_open):
        triggered = ctx.triggered_id

        if triggered == "uni-modal-close":
            return False, no_update

        if triggered == "uni-compare-btn" and selected and 2 <= len(selected) <= 4:
            cards   = [_compare_uni_card(name) for name in selected]
            content = html.Div(cards, className="compare-grid")
            return True, content

        return is_open, no_update
