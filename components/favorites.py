"""Widget 5 — Favorites + Compare (Tab 5)
Database: MongoDB
Type: UPDATE widget (R10) + Querying widget (R11)

Lists saved professors with remove buttons and checkboxes.
Selecting 2-4 opens a side-by-side compare modal.
"""
from dash import html, dcc, Input, Output, State, no_update, ctx, ALL
import dash_bootstrap_components as dbc

from utils.mongodb_utils import (
    get_favorites, remove_from_favorites, get_professor_profile
)

# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    favorites = get_favorites()   # fresh from MongoDB each time tab opens

    return html.Div([
        html.H2("Favorites", className="widget-title"),

        # ── Top bar ───────────────────────────────────────────────────────────
        html.Div([
            html.Span(
                f'{len(favorites)} saved professor{"s" if len(favorites) != 1 else ""}',
                id="fav-count",
                className="result-count",
                style={"flex": "1"},
            ),
            html.Div([
                html.Span(
                    "Select 2–4 professors to compare",
                    className="table-hint",
                    style={"marginRight": "12px"},
                ),
                html.Button(
                    "Compare Selected",
                    id="fav-compare-btn",
                    n_clicks=0,
                    className="btn-primary",
                    disabled=True,
                ),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={"display": "flex", "alignItems": "center",
                  "marginBottom": "16px", "flexWrap": "wrap", "gap": "8px"}),

        # ── Favorites list (re-rendered by callback) ──────────────────────────
        dcc.Store(id="fav-store", data=favorites),
        html.Div(id="fav-list-container"),

        # ── Compare modal ─────────────────────────────────────────────────────
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Professor Comparison")),
            dbc.ModalBody(html.Div(id="fav-modal-content")),
            dbc.ModalFooter(
                html.Button(
                    "Close",
                    id="fav-modal-close",
                    n_clicks=0,
                    className="btn-secondary",
                )
            ),
        ], id="fav-compare-modal", is_open=False, size="xl", scrollable=True),

    ], className="widget-container")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render_list(favorites):
    if not favorites:
        return html.P(
            "No favorites yet. Add professors from the Professor Profile tab.",
            className="placeholder",
        )

    rows = []
    for fav in favorites:
        name = fav.get("name", "")
        rows.append(html.Div([

            # Checkbox
            dcc.Checklist(
                id={"type": "fav-check", "index": name},
                options=[{"label": "", "value": name}],
                value=[],
                className="fav-checkbox-list",
            ),

            # Photo
            html.Img(
                src=fav.get("photo_url") or "https://via.placeholder.com/56?text=?",
                className="fav-photo",
            ),

            # Info
            html.Div([
                html.Strong(name, className="fav-name"),
                html.Span(fav.get("position", ""),   className="fav-detail fav-position"),
                html.Span(fav.get("university", ""), className="fav-detail"),
                html.Span(
                    f'{fav.get("pub_count", 0)} publications',
                    className="fav-detail fav-pubs",
                ),
                html.Div([
                    html.Span(kw, className="kw-badge-sm")
                    for kw in (fav.get("top_keywords") or [])
                ], className="kw-badge-list", style={"marginTop": "4px"}),
            ], className="fav-info"),

            # Remove button
            html.Button(
                "Remove",
                id={"type": "fav-remove", "index": name},
                n_clicks=0,
                className="btn-danger",
            ),

        ], className="fav-row"))

    return rows


def _compare_card(profile):
    """Single professor card for the comparison modal."""
    return html.Div([
        html.Img(
            src=profile.get("photo_url") or "https://via.placeholder.com/80?text=?",
            style={"width": "80px", "height": "80px", "objectFit": "cover",
                   "borderRadius": "40px", "border": "2px solid #2e6da4",
                   "marginBottom": "10px"},
        ),
        html.H5(profile["name"],     className="compare-name"),
        html.P(profile["position"],  className="compare-position"),
        html.P(profile["university"],className="compare-university"),
        html.Hr(style={"margin": "8px 0"}),
        html.P(
            f'{profile["pub_count"]} publications',
            style={"fontSize": "0.88rem", "fontWeight": "600", "color": "#2e6da4"},
        ),
        html.Div([
            html.Span(kw, className="kw-badge")
            for kw in profile["top_keywords"]
        ], className="kw-badge-list", style={"justifyContent": "center"}),
    ], className="compare-card")


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # 1. Render list whenever the store changes
    @app.callback(
        Output("fav-list-container", "children"),
        Output("fav-count", "children"),
        Input("fav-store", "data"),
    )
    def render_list(favorites):
        favorites = favorites or []
        count = f'{len(favorites)} saved professor{"s" if len(favorites) != 1 else ""}'
        return _render_list(favorites), count

    # 2. Remove a professor (pattern-matching over all remove buttons)
    @app.callback(
        Output("fav-store", "data"),
        Input({"type": "fav-remove", "index": ALL}, "n_clicks"),
        State("fav-store", "data"),
        prevent_initial_call=True,
    )
    def remove_professor(n_clicks_list, favorites):
        if not any(n_clicks_list):
            return no_update
        triggered = ctx.triggered_id
        if not triggered:
            return no_update
        name = triggered["index"]
        remove_from_favorites(name)
        return [f for f in (favorites or []) if f["name"] != name]

    # 3. Enable/disable Compare button based on checkbox selections
    @app.callback(
        Output("fav-compare-btn", "disabled"),
        Input({"type": "fav-check", "index": ALL}, "value"),
        prevent_initial_call=True,
    )
    def toggle_compare_btn(values_list):
        count = sum(1 for v in (values_list or []) if v)
        return not (2 <= count <= 4)

    # 4. Open/close compare modal
    @app.callback(
        Output("fav-compare-modal", "is_open"),
        Output("fav-modal-content", "children"),
        Input("fav-compare-btn",  "n_clicks"),
        Input("fav-modal-close",  "n_clicks"),
        State({"type": "fav-check", "index": ALL}, "value"),
        State({"type": "fav-check", "index": ALL}, "id"),
        State("fav-compare-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_modal(compare_clicks, close_clicks, values_list, id_list, is_open):
        triggered = ctx.triggered_id

        if triggered == "fav-modal-close":
            return False, no_update

        if triggered == "fav-compare-btn":
            selected = [
                id_["index"]
                for id_, val in zip(id_list or [], values_list or [])
                if val
            ]
            if len(selected) < 2:
                return False, no_update

            cards = []
            for name in selected:
                p = get_professor_profile(name)
                if p:
                    cards.append(_compare_card(p))

            return True, html.Div(cards, className="compare-grid")

        return is_open, no_update
