import sqlite3

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# --------------------------------------------------
# Må være første Streamlit-kall
# --------------------------------------------------

st.set_page_config(layout="wide")

# --------------------------------------------------
# Innstillinger
# --------------------------------------------------

GEOJSON_FILE = "20261025.geojson"
SOKN_FILE = "grefsen_soknegrenser.geojson"
SQLITE_FILE = "Talefot_antall_20261026.sqlite"

# Sett tabellnavn her hvis du kjenner det. None = bruker første tabell i filen.
SQLITE_TABELL = None

# Hardkodet liste med datoer. Legg til nye rader etter hvert (maks 10).
DATOER = [
    "torsdag  19   nov.  2026",
    "torsdag  17   des.  2026",
    # "…",  # legg til 2027-datoene her
]

# --------------------------------------------------
# Passord
# --------------------------------------------------

PASSWORD = st.secrets["PASSWORD"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:

    kode = st.text_input("Tilgangskode", type="password")

    if st.button("Logg inn"):
        if kode == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Feil kode")

    st.stop()

# --------------------------------------------------
# Datainnlasting (cachet)
# --------------------------------------------------

@st.cache_data
def last_ruter(path):
    return gpd.read_file(path)


@st.cache_data
def last_sokn(path):
    return gpd.read_file(path)


@st.cache_data
def last_antall(path, tabell=None):
    """Returnerer dict {rute: antall blader} fra SQLite."""
    con = sqlite3.connect(path)
    try:
        if tabell is None:
            tabell = pd.read_sql_query(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name",
                con,
            ).iloc[0, 0]
        df = pd.read_sql_query(f'SELECT * FROM "{tabell}"', con)
    finally:
        con.close()

    kol = {c.lower(): c for c in df.columns}
    rute_kol = next(c for k, c in kol.items() if k.startswith("rute"))
    antall_kol = next(c for k, c in kol.items() if k.startswith("ant"))

    df[rute_kol] = df[rute_kol].astype(str).str.strip()
    return dict(zip(df[rute_kol], df[antall_kol]))


gdf = last_ruter(GEOJSON_FILE)
sokn_gdf = last_sokn(SOKN_FILE)
antall_pr_rute = last_antall(SQLITE_FILE, SQLITE_TABELL)

st.title("Administrasjon av ruter")

# --------------------------------------------------
# Initialisering
# --------------------------------------------------

personer = sorted(gdf["fornavn_e"].dropna().unique().tolist())

if "selected_name" not in st.session_state:
    st.session_state.selected_name = personer[0]

# --------------------------------------------------
# Venstre marg
# --------------------------------------------------

valgt_person = st.sidebar.selectbox(
    "Velg områdeansvarlig",
    personer,
    index=personer.index(st.session_state.selected_name),
)

if valgt_person != st.session_state.selected_name:
    st.session_state.selected_name = valgt_person

antall = antall_pr_rute.get(str(st.session_state.selected_name).strip())

if antall is None:
    st.sidebar.metric("Antall blader", "–")
    st.sidebar.caption("Fant ikke ruten i SQLite-tabellen.")
else:
    st.sidebar.metric("Antall blader", f"{int(antall):,}".replace(",", " "))

st.sidebar.markdown("---")
st.sidebar.subheader("Datoer")
with st.sidebar.container(border=True):
    st.markdown("<br>".join(DATOER), unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### Lenker

    🔗 [Talefoten](https://talefoten.no/)

    ⛪ [Grefsen menighet](https://www.kirken.no/nb-NO/fellesrad/kirkeneioslo/menigheter/grefsen/)
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Valgt polygon
# --------------------------------------------------

selected = gdf[gdf["fornavn_e"] == st.session_state.selected_name].iloc[0]

minx, miny, maxx, maxy = selected.geometry.bounds

m = folium.Map(
    location=[(miny + maxy) / 2, (minx + maxx) / 2],
    zoom_start=15,
)
m.fit_bounds([[miny, minx], [maxy, maxx]])


def style_function(feature):
    navn = feature["properties"]["fornavn_e"]

    if navn == st.session_state.selected_name:
        return {
            "fillColor": "red",
            "color": "red",
            "weight": 4,
            "fillOpacity": 0.15,
        }

    return {
        "fillColor": "#3388ff",
        "color": "#3388ff",
        "weight": 2,
        "fillOpacity": 0.2,
    }


folium.GeoJson(
    sokn_gdf,
    style_function=lambda feature: {
        "fillOpacity": 0,
        "color": "darkgreen",
        "weight": 5,
    },
).add_to(m)

folium.GeoJson(
    gdf,
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=["fornavn_e"],
        aliases=["Ansvarlig"],
        sticky=True,
    ),
).add_to(m)

# --------------------------------------------------
# Hovedområde: kart (midten) + detaljer (høyre kolonne)
# --------------------------------------------------

map_data = st_folium(
    m,
    height=700,
    width=None,
    returned_objects=["last_object_clicked_tooltip"],
)

# --------------------------------------------------
# Håndter polygon-klikk
# --------------------------------------------------

if map_data:
    clicked = map_data.get("last_object_clicked_tooltip")

    if clicked:
        clean_name = clicked.replace("Ansvarlig", "").replace("\n", "").strip()

        if (
            clean_name
            and clean_name in personer
            and clean_name != st.session_state.selected_name
        ):
            st.session_state.selected_name = clean_name
            st.rerun()