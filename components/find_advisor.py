"""Widget 1 — Find Advisor (Tab 1)
Database: MySQL
Type: Querying widget (R11)

User searches by keyword; results table is sortable/filterable.
Clicking a row stores the professor name and switches to Tab 2.
"""
from dash import html, dcc, dash_table, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc

from utils.mysql_utils import get_all_universities, search_professors, call_get_top_professors

# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    universities = get_all_universities()
    uni_options  = [{"label": u, "value": u} for u in universities]

    return html.Div([
        html.H2("Find Advisor", className="widget-title"),

        # ── Controls ──────────────────────────────────────────────────────────
        html.Div([
            # Keyword input
            html.Div([
                html.Label("Research Keyword", className="control-label"),
                dcc.Input(
                    id="fa-keyword",
                    type="text",
                    placeholder="e.g. machine learning",
                    debounce=False,
                    className="control-input",
                ),
            ], className="control-group"),

            # Sort
            html.Div([
                html.Label("Sort By", className="control-label"),
                dcc.Dropdown(
                    id="fa-sort",
                    options=[
                        {"label": "Relevance Score", "value": "score"},
                        {"label": "Publication Count", "value": "pub_count"},
                        {"label": "Position",         "value": "position"},
                    ],
                    value="score",
                    clearable=False,
                    className="control-dropdown",
                ),
            ], className="control-group"),

            # University filter
            html.Div([
                html.Label("Filter by University", className="control-label"),
                dcc.Dropdown(
                    id="fa-university",
                    options=uni_options,
                    placeholder="All universities",
                    clearable=True,
                    className="control-dropdown",
                ),
            ], className="control-group control-group--wide"),

            # Position filter
            html.Div([
                html.Label("Filter by Position", className="control-label"),
                dcc.Dropdown(
                    id="fa-position",
                    options=[
                        {"label": "All",                    "value": "All"},
                        {"label": "Professor",              "value": "Professor"},
                        {"label": "Associate Professor",    "value": "Associate Professor"},
                        {"label": "Assistant Professor",    "value": "Assistant Professor"},
                    ],
                    value="All",
                    clearable=False,
                    className="control-dropdown",
                ),
            ], className="control-group"),

            # Search button
            html.Div([
                html.Button(
                    "Search",
                    id="fa-search-btn",
                    n_clicks=0,
                    className="btn-primary",
                ),
            ], className="control-group control-group--btn"),
        ], className="controls-row"),

        # ── Result count ──────────────────────────────────────────────────────
        html.Div(id="fa-result-count", className="result-count"),

        # ── Results table ─────────────────────────────────────────────────────
        html.Div(
            dash_table.DataTable(
                id="fa-table",
                columns=[
                    {"name": "Name",              "id": "name"},
                    {"name": "University",        "id": "university"},
                    {"name": "Position",          "id": "position"},
                    {"name": "Relevance Score",   "id": "score"},
                    {"name": "Publications",      "id": "pub_count"},
                ],
                data=[],
                page_size=20,
                sort_action="native",
                row_selectable=False,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#1a3a5c",
                    "color": "white",
                    "fontWeight": "600",
                    "fontSize": "0.85rem",
                    "padding": "10px 14px",
                    "border": "none",
                },
                style_cell={
                    "padding": "10px 14px",
                    "fontSize": "0.85rem",
                    "fontFamily": "Segoe UI, sans-serif",
                    "border": "1px solid #e8ecf0",
                    "maxWidth": "260px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "#f8fafc",
                    },
                    {
                        "if": {"state": "active"},
                        "backgroundColor": "#d0e8ff",
                        "border": "1px solid #2e6da4",
                        "cursor": "pointer",
                    },
                ],
                tooltip_data=[],
                tooltip_duration=None,
            ),
            className="table-wrapper",
        ),

        html.P(
            "Click any row to view the full professor profile.",
            className="table-hint",
            id="fa-table-hint",
            style={"display": "none"},
        ),
    ], className="widget-container")


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app):

    @app.callback(
        Output("fa-table", "data"),
        Output("fa-result-count", "children"),
        Output("fa-table-hint", "style"),
        Input("fa-search-btn", "n_clicks"),
        Input("fa-keyword", "n_submit"),   # also trigger on Enter key
        State("fa-keyword",    "value"),
        State("fa-sort",       "value"),
        State("fa-university", "value"),
        State("fa-position",   "value"),
        prevent_initial_call=True,
    )
    def run_search(n_clicks, n_submit, keyword, sort_by, university, position):
        if not keyword or not keyword.strip():
            return [], "Enter a keyword and press Search.", {"display": "none"}

        kw       = keyword.strip()
        sort_by  = sort_by or "score"
        uni      = university or None
        pos      = position if position != "All" else None

        # Use stored procedure (R14) for default relevance-score sort with no filters;
        # fall back to the flexible raw query when filters or alternate sort are applied.
        if sort_by == "score" and uni is None and pos is None:
            df = call_get_top_professors(kw, limit=200)
        else:
            df = search_professors(kw, sort_by=sort_by, university=uni, position=pos)

        if df.empty:
            return [], f'No results for "{keyword}".', {"display": "none"}

        df["score"] = df["score"].round(2)
        records = df[["name", "university", "position", "score", "pub_count"]].to_dict("records")
        count_msg = f'{len(df)} professor{"s" if len(df) != 1 else ""} found for "{keyword}"'
        return records, count_msg, {"display": "block"}

    @app.callback(
        Output("selected-professor-store", "data"),
        Output("tabs", "value"),
        Input("fa-table", "active_cell"),
        State("fa-table", "data"),
        prevent_initial_call=True,
    )
    def on_row_click(active_cell, table_data):
        if not active_cell or not table_data:
            return no_update, no_update
        row = active_cell["row"]
        if row >= len(table_data):
            return no_update, no_update
        professor_name = table_data[row]["name"]
        return professor_name, "tab-2"
