import logging
from pathlib import Path

import gravis as gv
import networkx as nx
import pandas as pd
import plotly.express as px
from pyvis.network import Network
import streamlit.components.v1 as components
import streamlit as st
import streamlit_authenticator as stauth
import yaml


directory = Path(__file__).parent
parent_directory = directory.parent

colors = px.colors.qualitative.Plotly


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

demo_dashboard_config = directory / 'config/flight_route_dashboard.yaml'


if __name__ == "__main__":

    with open(str(demo_dashboard_config), "r") as f:
        config = yaml.safe_load(f)

    local_data_paths = config['data_local_path']

    st.set_page_config(
        page_title='(Commercial Passenger) Flight Routes Network',
        page_icon='✈️',
        layout='wide'
    )

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

    name, authentication_status, username = authenticator.login(
        'main', fields={'Form name': 'Login to Flight Route Network Dashboard'}
    )

    if st.session_state["authentication_status"]:
        authenticator.logout()

        # Load data
        airports = pd.read_csv(local_data_paths['airports'])
        airlines = pd.read_csv(local_data_paths['airlines'])
        routes = pd.read_csv(local_data_paths['routes'])

        all_departure_airports = routes['Source airport'].unique()

        # planes = pd.read_csv(local_data_paths['planes'])

        input_col, fig_col1 = st.columns([1, 5])

        with input_col:

            departure_airport = st.selectbox(
                "Select the departure airport",
                sorted(all_departure_airports),
            )

            routes_from_departure_airport = routes[
                routes['Source airport'] == departure_airport
            ]

            routes_from_base_airport = pd.merge(
                routes_from_departure_airport,
                airports[['City', 'Country', 'IATA']],
                how='left',
                left_on='Destination airport',
                right_on='IATA'
            )
            routes_from_base_airport = routes_from_base_airport[
                [x for x in routes_from_base_airport.columns if x != 'IATA']
            ]
            routes_from_base_airport = pd.merge(
                routes_from_base_airport,
                airlines[['Name', 'IATA', 'Active']],
                how='left',
                left_on='Airline',
                right_on='IATA'
            )
            routes_from_base_airport = routes_from_base_airport[
                routes_from_base_airport['Active'] == 'Y'
            ]
            routes_from_base_airport['Airline, Full'] = routes_from_base_airport.apply(
                lambda x: f"{x['Airline']}, {x['Name']}", axis=1
            )

            all_available_airlines = routes_from_base_airport['Airline, Full'].unique()

            airline_container = st.container()
            all_airlines = st.checkbox("Select all airlines")

            if all_airlines:
                selected_airlines = airline_container.multiselect(
                    "Select operating airlines:",
                    all_available_airlines, all_available_airlines
                )
            else:
                selected_airlines = airline_container.multiselect(
                    "Select operating airlines:",
                    all_available_airlines
                )

            routes_from_base_airport_by_selected_airlines = routes_from_base_airport[
                routes_from_base_airport['Airline, Full'].isin(selected_airlines)
            ]

            all_available_countries = routes_from_base_airport_by_selected_airlines['Country'].unique()

            container = st.container()
            all_countries = st.checkbox("Select all arrival countries")

            if all_countries:
                selected_countries = container.multiselect(
                    "Select arrival countries:",
                    all_available_countries, all_available_countries
                )
            else:
                selected_countries = container.multiselect(
                    "Select arrival countries:",
                    all_available_countries
                )

            final_df = routes_from_base_airport_by_selected_airlines[
                routes_from_base_airport_by_selected_airlines['Country'].isin(selected_countries)
            ]

            # all_available_arrival_cities = routes_from_base_airport_to_selected_countries
            # all_arrival_airports = routes_from_base_airport_to_selected_countries['Destination airport'].unique()

        with fig_col1:

            st.title("Flight Route Network From Selected ✈️")

            G = nx.MultiGraph()

            # G.add_edge(selected_airline_base_country, departure_airport)

            for i, airline in enumerate(selected_airlines):

                airline_iata = airline.split(',')[0]

                temp_df = final_df[
                    final_df['Airline'] == airline_iata
                ]

                if len(selected_airlines) <= len(colors):
                    airline_color = colors[i]
                else:
                    airline_color = 'blue'

                G.add_edge(departure_airport, airline_iata)

                for country in temp_df['Country'].unique():

                    country_df = temp_df[
                        temp_df['Country'] == country
                    ]

                    G.add_edge(airline_iata, country, color=airline_color)

                    for city in country_df['City'].unique():

                        city_df = country_df[
                            country_df['City'] == city
                        ]

                        if city != country:
                            G.add_edge(country, city, label=airline_iata, color=airline_color)

                        for arrival_airport in city_df['Destination airport'].unique():
                            G.add_edge(city, arrival_airport, label=airline_iata, color=airline_color)

            d = nx.degree(G)

            for node in G.nodes:

                if node == departure_airport:
                    G.nodes[node]['size'] = 0.8
                    G.nodes[node]['color'] = colors[3]

                elif node in final_df['IATA'].unique() and node != departure_airport:

                    G.nodes[node]['size'] = 0.4

                elif len(node) == 3 and node.isalpha():

                    G.nodes[node]['size'] = 0.1
                    G.nodes[node]['color'] = colors[-1]
                elif node in final_df['Country'].unique():

                    G.nodes[node]['size'] = 0.5
                    G.nodes[node]['color'] = colors[1]

                else:
                    G.nodes[node]['color'] = colors[0]
                    G.nodes[node]['size'] = 0.2

            # nt = Network(directed=True)
            # nt.from_nx(G)
            # nt.set_edge_smooth('dynamic')

            fig = gv.d3(
                G,
                use_node_size_normalization=True,
                node_size_normalization_max=30,
                edge_curvature=0.6,
            )

            components.html(fig.to_html(), height=1000)

    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')


