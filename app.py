import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

from components.find_advisor import layout as find_advisor_layout, register_callbacks as fa_callbacks
from components.professor_profile import layout as professor_profile_layout, register_callbacks as pp_callbacks
from components.keyword_trends import layout as keyword_trends_layout, register_callbacks as kt_callbacks
from components.network import layout as network_layout, register_callbacks as net_callbacks
from components.favorites import layout as favorites_layout, register_callbacks as fav_callbacks
from components.universities import layout as universities_layout, register_callbacks as uni_callbacks
from components.my_notes import layout as my_notes_layout, register_callbacks as notes_callbacks

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = "AdvisorLens"

app.layout = html.Div(
    [
        # Header
        html.Div(
            [
                html.H1("AdvisorLens", className="header-title"),
                html.P(
                    "Find your perfect research advisor",
                    className="header-subtitle",
                ),
            ],
            className="header",
        ),
        # Tab navigation
        dcc.Tabs(
            id="tabs",
            value="tab-1",
            className="tab-bar",
            children=[
                dcc.Tab(label="Find Advisor",      value="tab-1", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Professor Profile", value="tab-2", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Keyword Trends",    value="tab-3", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Network",           value="tab-4", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Favorites",         value="tab-5", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="Universities",      value="tab-6", className="tab", selected_className="tab--selected"),
                dcc.Tab(label="My Notes",          value="tab-7", className="tab", selected_className="tab--selected"),
            ],
        ),
        # Tab content
        html.Div(id="tab-content", className="main-content"),
        # Cross-tab state
        dcc.Store(id="selected-professor-store"),
    ]
)


# ── Tab routing ───────────────────────────────────────────────────────────────

@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("selected-professor-store", "data"),
)
def render_tab(tab, selected_professor):
    if tab == "tab-1":
        return find_advisor_layout()
    elif tab == "tab-2":
        return professor_profile_layout(selected_professor)
    elif tab == "tab-3":
        return keyword_trends_layout()
    elif tab == "tab-4":
        return network_layout()
    elif tab == "tab-5":
        return favorites_layout()
    elif tab == "tab-6":
        return universities_layout()
    elif tab == "tab-7":
        return my_notes_layout()
    return html.Div("Tab not found")


# ── Register component callbacks ──────────────────────────────────────────────

fa_callbacks(app)
pp_callbacks(app)
kt_callbacks(app)
net_callbacks(app)
fav_callbacks(app)
uni_callbacks(app)
notes_callbacks(app)


if __name__ == "__main__":
    app.run(debug=True)
