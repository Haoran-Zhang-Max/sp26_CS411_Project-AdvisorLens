"""Widget 2 — Professor Profile (Tab 2)
Database: MongoDB
Type: Querying widget (R11)

Shows full profile card, top publications, keywords, and Add-to-Favorites.
Pre-loads a professor when navigated to from Tab 1.
"""
from dash import html, dcc, dash_table, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc

from utils.mongodb_utils import get_all_faculty_names, get_professor_profile, add_to_favorites, is_favorite

# ── Layout ────────────────────────────────────────────────────────────────────

def layout(selected_professor=None):
    names   = get_all_faculty_names()
    options = [{"label": n, "value": n} for n in names if n.strip()]

    return html.Div([
        html.H2("Professor Profile", className="widget-title"),

        # ── Search bar ────────────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Label("Professor Name", className="control-label"),
                dcc.Dropdown(
                    id="pp-name-dropdown",
                    options=options,
                    value=selected_professor,
                    placeholder="Search for a professor…",
                    clearable=True,
                    className="control-dropdown",
                    style={"minWidth": "320px"},
                ),
            ], className="control-group control-group--wide"),
        ], className="controls-row"),

        # ── Profile area (filled by callback) ────────────────────────────────
        html.Div(id="pp-profile-area", children=_empty_state()),

    ], className="widget-container")


def _empty_state():
    return html.P(
        "Search for a professor above to see their full profile.",
        className="placeholder",
    )


def _profile_card(p):
    """Build the full profile UI from a profile dict."""

    # ── Photo + basic info ────────────────────────────────────────────────────
    photo = html.Img(
        src=p["photo_url"] or "https://via.placeholder.com/120?text=No+Photo",
        className="profile-photo",
        style={"width": "120px", "height": "120px", "objectFit": "cover",
               "borderRadius": "60px", "border": "3px solid #2e6da4"},
    )

    info_rows = []
    if p["position"]:
        info_rows.append(html.P(p["position"],   className="profile-position"))
    if p["university"]:
        info_rows.append(html.P(p["university"], className="profile-university"))
    if p["email"]:
        info_rows.append(html.P([html.Strong("Email: "), p["email"]], className="profile-detail"))
    if p["research_interest"]:
        info_rows.append(html.P([html.Strong("Research: "), p["research_interest"]], className="profile-detail"))

    fav_already = is_favorite(p["name"])
    fav_btn = html.Button(
        "✓ In Favorites" if fav_already else "★ Add to Favorites",
        id="pp-fav-btn",
        n_clicks=0,
        className="btn-primary" if not fav_already else "btn-secondary",
        disabled=fav_already,
        style={"marginTop": "12px"},
    )
    fav_msg = html.Div(id="pp-fav-msg", style={"marginTop": "6px", "fontSize": "0.82rem", "color": "#2e7d32"})

    profile_left = html.Div([
        photo,
        html.H3(p["name"], className="profile-name", style={"marginTop": "12px"}),
        *info_rows,
        fav_btn,
        fav_msg,
    ], className="profile-left")

    # ── Keywords ──────────────────────────────────────────────────────────────
    kw_badges = [
        html.Span(kw["name"], className="kw-badge",
                  title=f"Score: {kw['score']}")
        for kw in p["keywords"]
    ]
    keywords_section = html.Div([
        html.H4("Top Keywords", className="section-subtitle"),
        html.Div(kw_badges, className="kw-badge-list"),
    ], className="profile-keywords")

    # ── Publications table ────────────────────────────────────────────────────
    pub_rows = p["publications"]
    pub_table = dash_table.DataTable(
        id="pp-pub-table",
        columns=[
            {"name": "Title",       "id": "title"},
            {"name": "Year",        "id": "year"},
            {"name": "Venue",       "id": "venue"},
            {"name": "Citations",   "id": "num_citations"},
        ],
        data=pub_rows,
        page_size=10,
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#1a3a5c", "color": "white",
            "fontWeight": "600", "fontSize": "0.82rem", "padding": "9px 12px",
        },
        style_cell={
            "padding": "9px 12px", "fontSize": "0.82rem",
            "fontFamily": "Segoe UI, sans-serif",
            "border": "1px solid #e8ecf0",
            "maxWidth": "360px", "overflow": "hidden", "textOverflow": "ellipsis",
        },
        style_cell_conditional=[
            {"if": {"column_id": "year"},         "width": "60px",  "textAlign": "center"},
            {"if": {"column_id": "num_citations"}, "width": "80px",  "textAlign": "center"},
        ],
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"}],
        tooltip_data=[
            {"title": {"value": row.get("title",""), "type": "text"}} for row in pub_rows
        ],
        tooltip_duration=None,
    )

    pubs_section = html.Div([
        html.H4(f"Top Publications  ({p['pub_count']} total)", className="section-subtitle"),
        pub_table,
    ], className="profile-pubs", style={"marginTop": "24px"})

    return html.Div([
        html.Div([profile_left, keywords_section], className="profile-top-row"),
        pubs_section,
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app):

    @app.callback(
        Output("pp-profile-area", "children"),
        Input("pp-name-dropdown", "value"),
        prevent_initial_call=False,   # run on load so pre-selected professor shows
    )
    def load_profile(name):
        if not name:
            return _empty_state()
        p = get_professor_profile(name)
        if not p:
            return html.P(f'Professor "{name}" not found in MongoDB.', className="placeholder")
        return _profile_card(p)

    @app.callback(
        Output("pp-fav-btn", "children"),
        Output("pp-fav-btn", "disabled"),
        Output("pp-fav-btn", "className"),
        Output("pp-fav-msg", "children"),
        Input("pp-fav-btn", "n_clicks"),
        State("pp-name-dropdown", "value"),
        prevent_initial_call=True,
    )
    def add_favorite(n_clicks, name):
        if not name:
            return no_update, no_update, no_update, no_update
        success = add_to_favorites(name)
        if success:
            return "✓ In Favorites", True, "btn-secondary", "Saved to your favorites!"
        return no_update, no_update, no_update, "Could not save — professor not found."
