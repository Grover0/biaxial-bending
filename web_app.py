import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from pandas_datareader import data as web
from datetime import datetime as dt

# Imports - project specific files
import regex_point_syntax

field_color = '#F5F5F5'
field_pad = 10
margin = 10

app = dash.Dash('Hello World')

app.layout = html.Div([
    dcc.Markdown('''
#### Test

Dash supports [Markdown](http://commonmark.org/help). \
$$ x^2 $$
Markdown is a simple way $d$ to write and format text.
It includes a syntax for things like **bold text** and *italics*,
[links](http://commonmark.org/help), inline `code` snippets, lists,
quotes, and more.
***
'''),
    html.Div(
        className='row',
        children=[
            html.Div(
                className='col s2 m2 l2',
                children=[
                    html.Div([
                        # Div for specifying the cross section vertices
                        # html.Label('Define cross section vertices'),
                        dcc.Input(
                            id='section-vertices',
                            placeholder='Syntax: (x1, y1), (x2, y2), ..., (xn, yn)',
                            type='text',
                            value='(-8, 8), (8, 8), (8, -8), (-8, -8)',
                            # style={'width': '100%'},
                        ),
                    ],),
                ], style={'backgroundColor': field_color, 'width': '47%', 'padding': field_pad, 'border-radius': 5,
                          'margin': margin, 'float': 'left'},
            ),
            html.Div(
                className='col s2 m2 l2',
                children=[
                    html.Div([
                        # Div for specifying the cross section vertices
                        dcc.Input(
                            id='rebar-locations',
                            placeholder='Syntax: (x1, y1), (x2, y2), ..., (xn, yn)',
                            # TODO See if there is a type containing only numbers and spceial characters ()[]{}
                            type='text',
                            value='(-5.6, 5.6), (0, 5.6), (5.6, 5.6), (5.6, 0), (5.6, -5.6), (0, -5.6), (-5.6, -5.6), (-5.6, 0)',
                            # style={'width': '100%'},
                        ),
                    ],),
                ], style={'backgroundColor': field_color, 'width': '47%', 'padding': field_pad, 'border-radius': 5,
                          'margin': margin, 'float': 'right'}
            ),
        ], style={'backgroundColor': '#FFFFFF', 'padding': 30, 'border-radius': 5},
    ),

    # Div for graphs
    html.Div(
        className='row',
        children=[
            html.Div(
                className='col s3 m3 l3',
                children=[
                    html.Div([
                        dcc.Graph(
                            id='section-plot',
                        ),
                    ]),
                ], style={'backgroundColor': field_color, 'width': '30%', 'padding': field_pad, 'border-radius': 5,
                          'margin': margin},
            ),
            html.Div(
                className='col s3 m3 l3',
                children=[
                    html.Div([
                        # dcc.Graph(
                        #     id='capacity-surface',
                        # ),
                    ], style={'backgroundColor': field_color, 'width': '30%', 'padding': field_pad, 'border-radius': 5,
                              'margin': margin}),
                ],
            ),
            html.Div(
                className='col s3 m3 l3',
                children=[
                    html.Div([
                        # dcc.Graph(
                        #     id='loads',
                        # ),
                    ], style={'backgroundColor': field_color, 'width': '30%', 'padding': field_pad, 'border-radius': 5,
                              'margin': margin}),
                ],
            ),
        ]
    ),

    # dcc.Dropdown(
    #     id = 'dropdown-to-hide-element',
    #     options=[
    #         {'label': 'Show element', 'value': 'on'},
    #         {'label': 'Hide element', 'value': 'off'}
    #     ],
    #     value = 'on'
    # ),
    
    # # Create Div to place a conditionally hidden element inside
    # html.Div([
    #     # Create element to hide, in this case an Input
    #     dcc.Input(
    #     id = 'element-to-hide',
    #     placeholder = 'something',
    #     type = 'something',
    #     value = 'Can you see me?',
    #     )
    # ])

    # ], style={'backgroundColor': 'grey'},),

# ], style={'color': 'black'},),

], className='container', style={'width': '95%'})

# @app.callback(
#     Output(component_id='element-to-hide', component_property='style'),
#     [Input(component_id='dropdown-to-hide-element', component_property='value')])

# def show_hide_element(visibility_state):
#     if visibility_state == 'on':
#         return {'display': 'block'}
#     if visibility_state == 'off':
#         return {'display': 'none'}


# UPDATE SECTION PLOT FOR CONCRETE GEOMETRY AND REBAR INPUT
@app.callback(
    Output(component_id='section-plot', component_property='figure'),
    [Input(component_id='section-vertices', component_property='value'),
    Input(component_id='rebar-locations', component_property='value')]
)
def update_section_plot(section_vertices, rebar_locations):

    # Extract only correctly typed points
    x, y, c = regex_point_syntax.get_points(section_vertices)       # Concrete section vertices
    xr, yr, _ = regex_point_syntax.get_points(rebar_locations)     # Rebar locations

    # TODO Check if polygon defined by concrete vertices intersects itself
    # TODO Check if rebars are all inside polygon, display the 'warning' as text below graph. If calculate button is ___
    # TODO ___ pressed, display 'critical error' to user.

    # Append first point to create a closed polygon
    if len(c) > 1:
        x.append(x[0])
        y.append(y[0])

    # Create plot
    concrete = go.Scatter(
        x = x,
        y = y,
        fill = 'toself',
        fillcolor = 'rgb(190, 190, 190)',
        mode = 'lines',
        line = dict(
            color = 'rgb(48,48,48)',
        ),
        opacity = 0.7,
        marker = {
            'size': 6,
            'line': {'width': 0.25, 'color': 'white'},
        },
    )
    rebars = go.Scatter(
        x = xr,
        y = yr,
        mode = 'markers',
        line = dict(
            color = 'rgb(20, 20, 20)',
        ),
        opacity = 0.7,
        marker = {
            'size': 10,
        },
    )

    return {
        'data': [concrete, rebars],
        'layout': go.Layout(
            # title = 'Cross Section Geometry',
            xaxis=dict(title='x', showgrid=False),
            yaxis=dict(title='y', scaleanchor='x', scaleratio=1,
                       showgrid=False), 
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            # margin = {'l': 50, 'b': 50, 't': 50, 'r': 50},
            hovermode='closest',
        )
    }


# # Update capacity surface
# @app.callback(
#     Output(component_id='capacity-surface', component_property='figure'),
#     [Input(component_id='section-vertices', component_property='value'),
#      Input(component_id='rebar-locations', component_property='value')]
# )
# def update_capacity_surface(section_vertices, rebar_locations):
#     # Plot points from analysis
#     # There should be a 'calculate' button
#     pass


external_css = ['https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/css/materialize.min.css']
# external_css = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

for css in external_css:
    app.css.append_css({'external_url': css})

for js in external_css:
    app.scripts.append_script({'external_url': js})

if __name__ == '__main__':
    app.run_server(debug=True)
