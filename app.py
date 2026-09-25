import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium

import streamlit as st

PASSWORD = "0047"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:

    kode = st.text_input(
        "Tilgangskode",
        type="password"
    )

    if st.button("Logg inn"):

        if kode == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()

        else:
            st.error("Feil kode")

    st.stop()

# --------------------------------------------------
# Last GeoJSON
# --------------------------------------------------

GEOJSON_FILE = r"20260705.geojson"

gdf = gpd.read_file(GEOJSON_FILE)

st.set_page_config(layout="wide")
st.title("Administrasjon av ruter")

# --------------------------------------------------
# Initialisering
# --------------------------------------------------

if "selected_name" not in st.session_state:
    st.session_state.selected_name = (
        gdf.iloc[0]["fornavn_e"]
    )

# --------------------------------------------------
# Dropdown
# --------------------------------------------------

personer = sorted(
    gdf["fornavn_e"].dropna().unique().tolist()
)

current_index = personer.index(
    st.session_state.selected_name
)

valgt_person = st.sidebar.selectbox(
    "Velg områdeansvarlig",
    personer,
    index=current_index
)

# Oppdater dersom dropdown brukes

if valgt_person != st.session_state.selected_name:
    st.session_state.selected_name = valgt_person

# --------------------------------------------------
# Valgt polygon
# --------------------------------------------------

selected = gdf[
    gdf["fornavn_e"] == st.session_state.selected_name
].iloc[0]

# --------------------------------------------------
# Zoom til polygon
# --------------------------------------------------

minx, miny, maxx, maxy = selected.geometry.bounds

center_lat = (miny + maxy) / 2
center_lon = (minx + maxx) / 2

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=15
)

m.fit_bounds([
    [miny, minx],
    [maxy, maxx]
])

# --------------------------------------------------
# Stil på polygoner
# --------------------------------------------------

def style_function(feature):

    navn = feature["properties"]["fornavn_e"]

    if navn == st.session_state.selected_name:
        return {
            "fillColor": "red",
            "color": "red",
            "weight": 4,
            "fillOpacity": 0.4,
        }

    return {
        "fillColor": "#3388ff",
        "color": "#3388ff",
        "weight": 2,
        "fillOpacity": 0.2,
    }

# --------------------------------------------------
# Kartlag
# --------------------------------------------------

geojson = folium.GeoJson(
    gdf,
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=["fornavn_e"],
        aliases=["Ansvarlig"],
        sticky=True
    )
)

geojson.add_to(m)

# --------------------------------------------------
# Vis kart
# --------------------------------------------------

map_data = st_folium(
    m,
    height=700,
    width=None,
    returned_objects=["last_object_clicked_tooltip"]
)

# --------------------------------------------------
# Håndter polygon-klikk
# --------------------------------------------------

if map_data:

    clicked = map_data.get(
        "last_object_clicked_tooltip"
    )

    if clicked:

        # Fjerner eventuell tekst fra tooltip
        clean_name = (
            clicked.replace("Ansvarlig", "")
                   .replace("\n", "")
                   .strip()
        )

        if (
            clean_name
            and clean_name in personer
            and clean_name != st.session_state.selected_name
        ):

            st.session_state.selected_name = clean_name
            st.rerun()

# --------------------------------------------------
# Detaljer
# --------------------------------------------------

st.sidebar.markdown("---")
st.sidebar.subheader("Detaljer")

st.sidebar.write(
    f"**Ansvarlig:** {selected['fornavn_e']}"
)

