"""Widget 4 — Network (Tab 4)
Database: Neo4j
Type: Querying widget (R11)

Interactive collaboration graph for a selected professor.
Nodes: the professor (gold), colleagues (blue), keywords (green).
Edges: faculty–keyword INTERESTED_IN, colleague–keyword shared links.
"""
from dash import html, dcc, Input, Output, State, no_update
import dash_cytoscape as cyto

from utils.neo4j_utils import get_all_faculty_names_neo4j, get_professor_network

# Load the cose-bilkent layout (better for large graphs)
cyto.load_extra_layouts()

# ── Layout ────────────────────────────────────────────────────────────────────

def layout():
    names   = get_all_faculty_names_neo4j()
    options = [{"label": n, "value": n} for n in names if n and n.strip()]

    return html.Div([
        html.H2("Collaboration Network", className="widget-title"),

        # ── Controls ──────────────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Label("Professor", className="control-label"),
                dcc.Dropdown(
                    id="net-professor",
                    options=options,
                    placeholder="Search for a professor…",
                    clearable=True,
                    searchable=True,
                    className="control-dropdown",
                    style={"minWidth": "280px"},
                ),
            ], className="control-group control-group--wide"),

            html.Div([
                html.Label("Layout", className="control-label"),
                dcc.Dropdown(
                    id="net-layout",
                    options=[
                        {"label": "Cose-Bilkent (default)", "value": "cose-bilkent"},
                        {"label": "Circle",                 "value": "circle"},
                        {"label": "Concentric",             "value": "concentric"},
                        {"label": "Breadth-first",          "value": "breadthfirst"},
                    ],
                    value="cose-bilkent",
                    clearable=False,
                    className="control-dropdown",
                    style={"minWidth": "180px"},
                ),
            ], className="control-group"),

            html.Div([
                html.Button("Load Graph", id="net-load-btn", n_clicks=0, className="btn-primary"),
            ], className="control-group control-group--btn"),
        ], className="controls-row"),

        # ── Status / legend ───────────────────────────────────────────────────
        html.Div([
            html.Span(id="net-status", className="result-count", style={"flex": "1"}),
            html.Div([
                html.Span("", className="legend-dot legend-dot--main"),
                html.Span("Selected professor", className="legend-label"),
                html.Span("", className="legend-dot legend-dot--faculty"),
                html.Span("Colleague",          className="legend-label"),
                html.Span("", className="legend-dot legend-dot--keyword"),
                html.Span("Keyword",            className="legend-label"),
            ], className="legend-row"),
        ], className="net-topbar"),

        # ── Graph canvas ──────────────────────────────────────────────────────
        cyto.Cytoscape(
            id="net-graph",
            elements=[],
            layout={"name": "cose-bilkent", "animate": True, "randomize": True},
            style={"width": "100%", "height": "520px",
                   "border": "1px solid #e8ecf0", "borderRadius": "6px",
                   "background": "#fafbfc"},
            stylesheet=_stylesheet(),
            responsive=True,
        ),

        # ── Node info panel ───────────────────────────────────────────────────
        html.Div(id="net-node-info", className="net-node-info"),

    ], className="widget-container")


def _stylesheet():
    return [
        # Base node
        {
            "selector": "node",
            "style": {
                "label":            "data(label)",
                "font-size":        "11px",
                "text-valign":      "bottom",
                "text-halign":      "center",
                "text-margin-y":    "4px",
                "color":            "#333",
                "width":            "36px",
                "height":           "36px",
                "border-width":     "2px",
                "border-color":     "#fff",
                "text-wrap":        "wrap",
                "text-max-width":   "120px",
            },
        },
        # Selected professor — gold
        {
            "selector": ".faculty_main",
            "style": {
                "background-color": "#f0a500",
                "width":  "52px",
                "height": "52px",
                "font-size":   "13px",
                "font-weight": "bold",
                "color":       "#1a3a5c",
                "border-color": "#c47d00",
                "border-width": "3px",
            },
        },
        # Colleague — blue
        {
            "selector": ".faculty",
            "style": {
                "background-color": "#2e6da4",
                "color": "#1a3a5c",
            },
        },
        # Keyword — teal/green
        {
            "selector": ".keyword",
            "style": {
                "background-color": "#27ae60",
                "color":            "#1a3a5c",
                "width":  "28px",
                "height": "28px",
                "font-size": "10px",
                "shape": "round-rectangle",
            },
        },
        # Edges
        {
            "selector": "edge",
            "style": {
                "width":            "1.5px",
                "line-color":       "#b0c4d8",
                "curve-style":      "bezier",
                "opacity":          "0.7",
            },
        },
        # Hover highlight
        {
            "selector": "node:selected",
            "style": {
                "border-color":  "#f0a500",
                "border-width":  "3px",
                "overlay-color": "#f0a500",
                "overlay-opacity": "0.15",
            },
        },
    ]


def _to_cyto_elements(network):
    """Convert {nodes, edges} dict to Cytoscape elements list."""
    elements = []
    for node in network["nodes"]:
        elements.append({
            "data":    {"id": node["id"], "label": node["label"]},
            "classes": node["type"],
        })
    for edge in network["edges"]:
        elements.append({
            "data": {
                "source": edge["source"],
                "target": edge["target"],
                "id":     f"{edge['source']}__{edge['target']}",
            }
        })
    return elements


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks(app):

    @app.callback(
        Output("net-graph",  "elements"),
        Output("net-graph",  "layout"),
        Output("net-status", "children"),
        Input("net-load-btn",  "n_clicks"),
        Input("net-professor", "value"),
        State("net-layout",    "value"),
        prevent_initial_call=True,
    )
    def load_graph(n_clicks, professor, layout_name):
        if not professor:
            return [], {"name": "cose-bilkent"}, "Select a professor to visualise their network."

        net      = get_professor_network(professor)
        elements = _to_cyto_elements(net)

        faculty_count = sum(1 for n in net["nodes"] if n["type"] == "faculty")
        kw_count      = sum(1 for n in net["nodes"] if n["type"] == "keyword")

        if faculty_count == 0 and kw_count == 0:
            status = f'No network data found for "{professor}" — they may not exist in the graph.'
        else:
            status = (
                f'{faculty_count} colleague{"s" if faculty_count != 1 else ""}  ·  '
                f'{kw_count} shared keyword{"s" if kw_count != 1 else ""}  ·  '
                f'{len(net["edges"])} connections'
            )

        cy_layout = {
            "name":      layout_name or "cose-bilkent",
            "animate":   True,
            "randomize": True,
        }
        return elements, cy_layout, status

    @app.callback(
        Output("net-node-info", "children"),
        Input("net-graph", "tapNodeData"),
        prevent_initial_call=True,
    )
    def show_node_info(node_data):
        if not node_data:
            return ""
        label = node_data.get("label", "")
        return html.Span(f'Selected: {label}', style={"fontWeight": "600", "color": "#1a3a5c"})
