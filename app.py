# Import relevant libraries
import pandas as pd
from sodapy import Socrata
import requests
import base64
from urllib.parse import urlencode
from datetime import datetime, timedelta
import plotly.express as px
#from plotly import graph_objs as go
#from plotly.graph_objs import *

#import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from io import StringIO
import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# py/python -m venv .venv
# .venv\Scripts\activate
# pip install -r requirements.txt
# activate venv and run program py app.py

# requirements plotly==2.15.0
# dotenv

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}],)
app.title = "Site Viewer"
server = app.server

load_dotenv()
socrata_api_id = os.getenv("socrata_api_id")
socrata_api_secret = os.getenv("socrata_api_secret")


# Plotly mapbox public token
mapbox_access_token = "pk.eyJ1IjoicGxvdGx5bWFwYm94IiwiYSI6ImNrOWJqb2F4djBnMjEzbG50amg0dnJieG4ifQ.Zme1-Uzoi75IaFbieBDl3A"

app.layout = html.Div(
    children=[
        html.Div(
            className="row", 
            children=[
                # Column for user controls
                html.Div(
                    className="four columns div-user-controls",  # mobil/desktop transition needs eight and 4 column
                    children=[
                        html.H2("Telemetered Sites"),
                        html.P("""displays basic infomation for telemetered sites based on Socrata copy of gData"""),
                        html.Button('Refresh Data', id='refresh-button', n_clicks=0),
                        #html.Div(className="div-for-dropdown",children=[dcc.DatePickerSingle(id="date-picker",style={"border": "0px solid black"},)],),
                        # Change to side-by-side for mobile layout
                        html.Div(
                            className="row",
                            children=[
                                html.P("""select a parameter"""),
                                html.Div(className="div-for-dropdown",children=[dcc.Dropdown(id="parameter",options=[{"label": "discharge", "value": "discharge"},{"label": "battery volts", "value": "battery_volts"},],value="battery_volts",clearable=False,),],),
                                #html.Div(className="div-for-dropdown",children=[dcc.Dropdown(id="bar-selector",multi=True,)],),
                            ],
                        ),
                        html.P(id="total-rides"),
                        html.P(id="total-rides-selection"),
                        html.P(id="date-value"),
                    ],
                ),
                # Column for app graphs and plots
                
                #html.Div(className="eight columns div-for-charts bg-grey",children=[
                #    dcc.Graph(id='battery-graph', responsive = False),
                #    #dcc.Graph(id="histogram"),
                #    ],),
                html.Div(
                    className="eight columns div-for-charts bg-grey", # mobil/desktop transition needs eight and 4 column
                    children=[
                        dcc.Graph(id="battery-graph"),
                        html.Div(
                            className="text-padding",
                            children=[
                                "placeholder for additional graph"
                            ],),
                        # dcc.Graph(id="histogram"),  # Uncomment if needed and adjust layout accordingly
                    ],
                ),
            ],
        ),
        dcc.Store(id = 'metadata'), # store site metadata
        dcc.Store(id = 'gagers'), # store gager list
        dcc.Store(id = 'telemetry'), # store telemetry
        dcc.Store(id = 'last_data'), # stores last data value
    ],
        
)
# Define the layout of the dashboard
@app.callback(
    Output('metadata', 'data'),
    Output('gagers', 'data'),
    Input('refresh-button', 'n_clicks')
)
# Define functions as in your original code
def site_metadata(n_clicks):
    """reads site meta data, returns sites and gager list"""
    socrata_database_id = "g7er-dgc7"
    dataset_url = f"https://data.kingcounty.gov/resource/{socrata_database_id}.json"
    socrataUserPw = (f"{socrata_api_id}:{socrata_api_secret}").encode('utf-8')
    base64AuthToken = base64.b64encode(socrataUserPw)
    headers = {'accept': '*/*', 'Authorization': 'Basic ' + base64AuthToken.decode('utf-8')}
    query_params = {
        "$select": "site, latitude, longitude, gager",
        "$where": f"telemetry_status == 'True'"
    }
    
    encoded_query = urlencode(query_params)
    dataset_url = f"{dataset_url}?{encoded_query}"
    
    response = requests.get(dataset_url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        
        gager_list = df["gager"].drop_duplicates().tolist()
        df = df.to_json(orient="split")
    else:
        return dash.no_update 
    return df, gager_list


@app.callback(
    Output('telemetry', 'data'),
    Input('metadata', 'data'),
)
def telemetry_status(metadata):
    """triggers if metadata is changed (refresh is clicked)"""
    if metadata:
        socrata_database_id = "gzfg-8xtp"
        dataset_url = f"https://data.kingcounty.gov/resource/{socrata_database_id}.json"
        socrataUserPw = (f"{socrata_api_id}:{socrata_api_secret}").encode('utf-8')
        base64AuthToken = base64.b64encode(socrataUserPw)
        headers = {'accept': '*/*', 'Authorization': 'Basic ' + base64AuthToken.decode('utf-8')}

        
        today = datetime.now().astimezone(ZoneInfo("Etc/GMT+7"))
        yesterday = datetime.now().astimezone(ZoneInfo("Etc/GMT+7")) - timedelta(days=1)
        query_params = {
            "$select": "site, datetime as voltage_date, battery_volts",
            "$where": f"datetime >= '{yesterday.strftime('%Y-%m-%d')}' AND datetime < '{today.strftime('%Y-%m-%d')}'"
        }
        encoded_query = urlencode(query_params)
        dataset_url = f"{dataset_url}?{encoded_query}"
        
        response = requests.get(dataset_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            df["voltage_date"] = pd.to_datetime(df['voltage_date'])
            df["voltage_date"]  = df["voltage_date"].dt.strftime('%Y-%m-%d %H:%M')
           
            df = df.to_json(orient="split")
            return df
        else:
            return dash.no_update
        
    else:
        return dash.no_update



@app.callback(
    Output('last_data', 'data'),
    Input('metadata', 'data'),
    Input("parameter", 'value')
)
def last_data(metadata, parameter):
    if metadata and parameter and parameter == "discharge":
        #metadata = pd.DataFrame(metadata)
        #metadata = pd.read_json(metadata, orient="split")
        #metadata = pd.read_json(StringIO(metadata), orient="split")
        #site_list = metadata["site"].tolist()
        

        #socrata_api_id = "37ja57noqzsdkkeo5ox34pfzm"
        #socrata_api_secret = "4i1u1tyb6mfivhnw2fqhhsrim675gurrw8g1zegdwomix9xj91"
        socrata_database_id = "hkim-5ysi"
        dataset_url = f"https://data.kingcounty.gov/resource/{socrata_database_id}.json"
        socrataUserPw = (f"{socrata_api_id}:{socrata_api_secret}").encode('utf-8')
        base64AuthToken = base64.b64encode(socrataUserPw)
        headers = {'accept': '*/*', 'Authorization': 'Basic ' + base64AuthToken.decode('utf-8')}

        today = datetime.now().astimezone(ZoneInfo("Etc/GMT+7"))
        

        yesterday = datetime.now().astimezone(ZoneInfo("Etc/GMT+7")) - timedelta(hours=12)
       
        #print("today: ", today, " yesterday: ", yesterday)
        #query_params = {
        #    "$select": f"site_id as site, datetime as last_log, corrected_data as {parameter}",
        #    "$where": f"parameter == '{parameter}' AND last_log > '{yesterday.strftime('%Y-%m-%d %h:%m')}' AND last_log < '{today.strftime('%Y-%m-%d %h:%m')}'",
            
            #"$group": "site"
            
        #}

        query_params = {
            "$select": f"site_id as site, datetime as last_log, corrected_data as {parameter}",
            "$where": f"parameter == '{parameter}' AND last_log >= '{yesterday.strftime('%Y-%m-%d')}'",
            "$limit": "10000",
            
            #"$group": "site"
            
        }
       
        
        #"$where": f"last_log >= '{yesterday.strftime('%Y-%m-%d')}' AND last_log < '{today.strftime('%Y-%m-%d')}'"
        #"$where": f"datetime >= '{yesterday.strftime('%Y-%m-%d')}' AND datetime < '{today.strftime('%Y-%m-%d')}'"
        encoded_query = urlencode(query_params)
        dataset_url = f"{dataset_url}?{encoded_query}"
        
        response = requests.get(dataset_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            df = pd.DataFrame(data)
            #print("int discharge df")
            #print(df)
            #print(df.loc[df["site"] == "68A"])
            df["last_log"] = pd.to_datetime(df['last_log'])
            max_last_log = df.groupby('site')['last_log'].max().reset_index()

            # Merge to get the corresponding `discharge` values
            df = pd.merge(max_last_log, df, on=['site', 'last_log'], how='left')
            #print("int discharge df")
            
            #print(df.loc[df["site"] == "68A"])

            df["last_log"]  = df["last_log"].dt.strftime('%Y-%m-%d %H:%M')
          
        
            df = df.to_json(orient="split")
            return df
        else:
            #print(response)
            return dash.no_update
    else:
        return dash.no_update


@app.callback(
    Output('battery-graph', 'figure'),
    Input('metadata', 'data'),
    Input('telemetry', 'data'),
    Input('last_data', 'data'),
    Input("parameter", 'value'),
)
def create_battery_graph(metadata, telemetry, last_data, parameter):
    
   
    
    if metadata and telemetry:
        metadata = pd.read_json(StringIO(metadata), orient="split")
        telemetry = pd.read_json(StringIO(telemetry), orient="split")
        df = metadata.merge(telemetry, on="site", how = "left")
    
        #print("base data")
        #print(df)
        if last_data and parameter == "discharge":
            last_data = pd.read_json(StringIO(last_data), orient="split")
            df = last_data.merge(df, on="site", how = "left") # left would include all sides and discharge data
            #print("discharge")
            #print(df)
        df = df.fillna("")
        
       
        df["longitude"] = pd.to_numeric(df['longitude'], errors='coerce')
        df["latitude"] = pd.to_numeric(df['latitude'], errors='coerce')
        df["battery_volts"] = pd.to_numeric(df['battery_volts'], errors='coerce')
        
        df['color_category'] = "grey"

        
        df.loc[df["battery_volts"] < 11.8, 'color_category'] = 11.9
        df.loc[(df["battery_volts"] >= 11.8) & (df["battery_volts"] < 12.0), 'color_category'] = 12.0
        df.loc[(df["battery_volts"] >= 12.0) & (df["battery_volts"] < 12.2), 'color_category'] = 12.2
        df.loc[(df["battery_volts"] >= 12.2) & (df["battery_volts"] < 12.4), 'color_category'] = 12.4
        df.loc[(df["battery_volts"] >= 12.4) & (df["battery_volts"] < 12.6), 'color_category'] = 12.6
        df.loc[(df["battery_volts"] >= 12.6) & (df["battery_volts"] < 13), 'color_category'] = 12.9
        df.loc[df["battery_volts"] >= 13, 'color_category'] = 13

        df['color_category'] = pd.to_numeric(df['color_category'], errors='coerce')

    
       
        if "discharge" in df.columns:
            hover_data = {"discharge": True, "last_log": True, "voltage_date": False, "battery_volts": True, "latitude": False, "longitude": False, "color_category": False}
        if not "discharge" in df.columns:
             hover_data = {"voltage_date": True, "battery_volts": True, "latitude": False, "longitude": False, "color_category": False}
        fig = px.scatter_map(df,
                            lat=df["latitude"],
                            lon=df["longitude"],
                            color=df['color_category'],
                            hover_name="site",
                            hover_data=hover_data,
                            color_continuous_scale=px.colors.sequential.GnBu,
                
                            zoom=9)
       
        fig.update_traces(marker=dict(size=10))
        fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0,  # Position at the bottom
            xanchor="center",
            x=0.5  # Center horizontally
        ),
        autosize=False,  # Disable autosizing to set a custom height
        height = 800,
        
         #
        margin=dict(l=0, r=0, t=0, b=0),
        
        #mapbox_style=py"open-street-map"  # Add map style if not already defined
        )
        return fig
        
    else:
        return dash.no_update
        

if __name__ == '__main__':
    app.run_server(debug=False)
    
