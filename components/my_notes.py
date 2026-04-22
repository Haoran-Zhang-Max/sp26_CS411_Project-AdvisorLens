"""Widget 7 — My Notes (Tab 7)
Database: MongoDB
Type: UPDATE widget (R10)

Write personal notes and star ratings (1–5) for any professor.
Existing note for the selected professor auto-loads into the form for editing.
"""
from dash import html, dcc, Input, Output, State, no_update, ctx, ALL

from utils.mongodb_utils import (
    get_all_faculty_names, get_all_notes, get_note, save_note, delete_note
)

# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    names   = get_all_faculty_names()
    options = [{"label": n, "value": n} for n in names if n.strip()]
    notes   = get_all_notes()

    return html.Div([
        html.H2("My Notes", className="widget-title"),

        # ── Input form ────────────────────────────────────────────────────────
        html.Div([

            # Professor dropdown
            html.Div([
                html.Label("Professor", className="control-label"),
                dcc.Dropdown(
                    id="notes-professor",
                    options=options,
                    placeholder="Search for a professor…",
                    clearable=True,
                    searchable=True,
                    className="control-dropdown",
                    style={"minWidth": "280px"},
                ),
            ], className="control-group control-group--wide"),

            # Star rating
            html.Div([
                html.Label("Rating", className="control-label"),
                dcc.RadioItems(
                    id="notes-rating",
                    options=[
                        {"label": "★",     "value": 1},
                        {"label": "★★",   "value": 2},
                        {"label": "★★★",  "value": 3},
                        {"label": "★★★★", "value": 4},
                        {"label": "★★★★★","value": 5},
                    ],
                    value=3,
                    inline=True,
                    className="star-radio",
                    inputStyle={"marginRight": "3px"},
                    labelStyle={"marginRight": "10px", "fontSize": "1.05rem",
                                "cursor": "pointer", "color": "#f0a500"},
                ),
            ], className="control-group"),

        ], className="controls-row"),

        # Note textarea + buttons
        html.Div([
            html.Label("Note", className="control-label"),
            dcc.Textarea(
                id="notes-text",
                placeholder="Write your notes about this professor…",
                style={
                    "width": "100%", "height": "110px",
                    "padding": "10px 12px", "fontSize": "0.875rem",
                    "border": "1px solid #ced4da", "borderRadius": "4px",
                    "resize": "vertical", "fontFamily": "Segoe UI, sans-serif",
                    "outline": "none",
                },
            ),
        ], style={"marginBottom": "12px"}),

        html.Div([
            html.Button("Save Note",   id="notes-save-btn",   n_clicks=0,
                        className="btn-primary",   style={"marginRight": "10px"}),
            html.Button("Delete Note", id="notes-delete-btn", n_clicks=0,
                        className="btn-danger",    disabled=True),
            html.Span(id="notes-form-msg",
                      style={"marginLeft": "14px", "fontSize": "0.85rem",
                             "color": "#2e7d32", "fontWeight": "500"}),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "28px"}),

        # ── Saved notes list ──────────────────────────────────────────────────
        html.Hr(style={"marginBottom": "20px"}),
        html.H3("All Notes", style={"fontSize": "1rem", "fontWeight": "600",
                                     "color": "#1a3a5c", "marginBottom": "12px"}),
        dcc.Store(id="notes-store", data=notes),
        html.Div(id="notes-list-container"),

    ], className="widget-container")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _star_display(rating):
    filled = "★" * int(rating)
    empty  = "☆" * (5 - int(rating))
    return html.Span(filled + empty,
                     style={"color": "#f0a500", "fontSize": "1.1rem", "letterSpacing": "1px"})


def _render_notes(notes):
    if not notes:
        return html.P("No notes saved yet.", className="placeholder",
                      style={"padding": "20px 0"})

    cards = []
    for note in notes:
        name    = note.get("professor_name", "")
        rating  = note.get("rating", 0)
        text    = note.get("note", "")
        updated = note.get("updated_at", "")
        if updated:
            try:
                updated = updated.strftime("%b %d, %Y")
            except Exception:
                updated = str(updated)[:10]

        cards.append(html.Div([
            # Header row
            html.Div([
                html.Div([
                    html.Strong(name, className="note-prof-name"),
                    html.Span(f" · {updated}", className="note-date"),
                ]),
                html.Div([
                    _star_display(rating),
                    html.Button(
                        "Delete",
                        id={"type": "note-delete-btn", "index": name},
                        n_clicks=0,
                        className="btn-danger",
                        style={"marginLeft": "12px", "height": "28px"},
                    ),
                ], style={"display": "flex", "alignItems": "center"}),
            ], className="note-header"),

            # Note body
            html.P(text, className="note-body"),
        ], className="note-card"))

    return cards


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app):

    # 1. Auto-load existing note when professor is selected
    @app.callback(
        Output("notes-text",       "value"),
        Output("notes-rating",     "value"),
        Output("notes-delete-btn", "disabled"),
        Input("notes-professor",   "value"),
        prevent_initial_call=True,
    )
    def load_existing_note(professor):
        if not professor:
            return "", 3, True
        existing = get_note(professor)
        if existing:
            return existing.get("note", ""), existing.get("rating", 3), False
        return "", 3, True

    # 2. Save note
    @app.callback(
        Output("notes-store",     "data"),
        Output("notes-form-msg",  "children"),
        Output("notes-delete-btn","disabled", allow_duplicate=True),
        Input("notes-save-btn",   "n_clicks"),
        State("notes-professor",  "value"),
        State("notes-rating",     "value"),
        State("notes-text",       "value"),
        prevent_initial_call=True,
    )
    def on_save(n_clicks, professor, rating, text):
        if not professor:
            return no_update, "Please select a professor first.", no_update
        if not text or not text.strip():
            return no_update, "Please write something in the note.", no_update
        save_note(professor, rating or 3, text.strip())
        updated_notes = get_all_notes()
        return updated_notes, f'Note saved for {professor}!', False

    # 3. Delete note from form
    @app.callback(
        Output("notes-store",    "data",     allow_duplicate=True),
        Output("notes-form-msg", "children", allow_duplicate=True),
        Output("notes-text",     "value",    allow_duplicate=True),
        Output("notes-rating",   "value",    allow_duplicate=True),
        Output("notes-delete-btn","disabled", allow_duplicate=True),
        Input("notes-delete-btn","n_clicks"),
        State("notes-professor", "value"),
        prevent_initial_call=True,
    )
    def on_form_delete(n_clicks, professor):
        if not professor:
            return no_update, no_update, no_update, no_update, no_update
        delete_note(professor)
        return get_all_notes(), f'Note for {professor} deleted.', "", 3, True

    # 4. Delete note from list (pattern-matching)
    @app.callback(
        Output("notes-store",    "data",     allow_duplicate=True),
        Output("notes-form-msg", "children", allow_duplicate=True),
        Input({"type": "note-delete-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def on_list_delete(n_clicks_list):
        if not any(n_clicks_list):
            return no_update, no_update
        triggered = ctx.triggered_id
        if not triggered:
            return no_update, no_update
        name = triggered["index"]
        delete_note(name)
        return get_all_notes(), f'Note for {name} deleted.'

    # 5. Render notes list from store
    @app.callback(
        Output("notes-list-container", "children"),
        Input("notes-store", "data"),
    )
    def render_notes(notes):
        return _render_notes(notes or [])
