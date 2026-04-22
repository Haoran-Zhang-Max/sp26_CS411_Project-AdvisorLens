"""Widget 3 — Keyword Trends (Tab 3)
Database: MySQL
Type: Querying widget (R11)

Shows a line/bar chart of publications per year for a given keyword,
with optional university and professor filters.
"""
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

from utils.mysql_utils import get_all_universities, get_all_keywords, get_all_faculty_names, get_keyword_trend

# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    keywords    = get_all_keywords()
    universities = get_all_universities()
    professors   = get_all_faculty_names()

    kw_options   = [{"label": k, "value": k} for k in keywords]
    uni_options  = [{"label": u, "value": u} for u in universities]
    prof_options = [{"label": p, "value": p} for p in professors if p.strip()]

    return html.Div([
        html.H2("Keyword Trends", className="widget-title"),

        # ── Controls ──────────────────────────────────────────────────────────
        html.Div([
            # Keyword (required)
            html.Div([
                html.Label("Keyword", className="control-label"),
                dcc.Dropdown(
                    id="kt-keyword",
                    options=kw_options,
                    placeholder="e.g. deep learning",
                    clearable=True,
                    searchable=True,
                    className="control-dropdown",
                    style={"minWidth": "200px"},
                ),
            ], className="control-group control-group--wide"),

            # University filter
            html.Div([
                html.Label("Filter by University", className="control-label"),
                dcc.Dropdown(
                    id="kt-university",
                    options=uni_options,
                    placeholder="All universities",
                    clearable=True,
                    searchable=True,
                    className="control-dropdown",
                ),
            ], className="control-group control-group--wide"),

            # Professor filter
            html.Div([
                html.Label("Filter by Professor", className="control-label"),
                dcc.Dropdown(
                    id="kt-professor",
                    options=prof_options,
                    placeholder="All professors",
                    clearable=True,
                    searchable=True,
                    className="control-dropdown",
                ),
            ], className="control-group control-group--wide"),

            # Chart type toggle
            html.Div([
                html.Label("Chart Type", className="control-label"),
                dcc.RadioItems(
                    id="kt-chart-type",
                    options=[
                        {"label": " Line", "value": "line"},
                        {"label": " Bar",  "value": "bar"},
                    ],
                    value="line",
                    inline=True,
                    className="radio-items",
                ),
            ], className="control-group"),

            # Search button
            html.Div([
                html.Button(
                    "Show Trend",
                    id="kt-search-btn",
                    n_clicks=0,
                    className="btn-primary",
                ),
            ], className="control-group control-group--btn"),
        ], className="controls-row"),

        # ── Status message ────────────────────────────────────────────────────
        html.Div(id="kt-status", className="result-count"),

        # ── Chart ─────────────────────────────────────────────────────────────
        dcc.Graph(
            id="kt-chart",
            figure=_empty_figure(),
            config={"displayModeBar": True, "displaylogo": False},
            style={"height": "460px"},
        ),

    ], className="widget-container")


def _empty_figure():
    fig = px.line(title="Enter a keyword above and click Show Trend")
    fig.update_layout(
        plot_bgcolor="#fafbfc",
        paper_bgcolor="#ffffff",
        font_family="Segoe UI, sans-serif",
        title_font_color="#888",
        title_x=0.5,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def _build_figure(df, keyword, chart_type, subtitle):
    """Render the trend chart from a DataFrame with columns year, pub_count."""
    title = f'Publication Trend — "{keyword}"'
    if subtitle:
        title += f"<br><sup>{subtitle}</sup>"

    if chart_type == "bar":
        fig = px.bar(
            df, x="year", y="pub_count",
            labels={"year": "Year", "pub_count": "Publications"},
            title=title,
            color_discrete_sequence=["#2e6da4"],
        )
    else:
        fig = px.line(
            df, x="year", y="pub_count",
            labels={"year": "Year", "pub_count": "Publications"},
            title=title,
            markers=True,
            color_discrete_sequence=["#2e6da4"],
        )
        fig.update_traces(line_width=2.5, marker_size=7)

    fig.update_layout(
        plot_bgcolor="#fafbfc",
        paper_bgcolor="#ffffff",
        font_family="Segoe UI, sans-serif",
        title_font_size=15,
        title_x=0.5,
        hovermode="x unified",
        xaxis=dict(
            title="Year",
            tickmode="linear",
            dtick=1,
            gridcolor="#e8ecf0",
        ),
        yaxis=dict(
            title="Number of Publications",
            gridcolor="#e8ecf0",
        ),
        margin=dict(l=60, r=30, t=70, b=50),
    )
    return fig


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app):

    @app.callback(
        Output("kt-chart",  "figure"),
        Output("kt-status", "children"),
        Input("kt-search-btn", "n_clicks"),
        Input("kt-keyword",    "value"),   # also trigger when dropdown selection changes
        State("kt-keyword",    "value"),
        State("kt-university", "value"),
        State("kt-professor",  "value"),
        State("kt-chart-type", "value"),
        prevent_initial_call=True,
    )
    def update_chart(n_clicks, kw_input, keyword, university, professor, chart_type):
        # kw_input (Input) and keyword (State) are the same field — use whichever is set
        kw = keyword or kw_input
        if not kw:
            return _empty_figure(), "Select a keyword to see its publication trend."

        df = get_keyword_trend(kw, university=university, professor=professor)

        if df.empty:
            return _empty_figure(), f'No publications found for "{kw}" with the selected filters.'

        # Build subtitle from active filters
        parts = []
        if university: parts.append(university)
        if professor:  parts.append(professor)
        subtitle = " · ".join(parts) if parts else ""

        fig    = _build_figure(df, kw, chart_type or "line", subtitle)
        total  = int(df["pub_count"].sum())
        peak   = df.loc[df["pub_count"].idxmax()]
        status = (
            f'{total:,} total publications across {len(df)} years  '
            f'(peak: {int(peak["pub_count"])} in {int(peak["year"])})'
        )
        return fig, status
