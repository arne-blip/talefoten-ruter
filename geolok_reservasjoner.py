
    #url = "https://ws.geonorge.no/adresser/v1/sok"

import json
import re
import time
import pandas as pd
import requests


def rens_adresse(tekst):
    """Fjerner automatisk leilighetsnummer, etasjer og tekst etter komma."""
    if pd.isna(tekst):
        return ""
    tekst = str(tekst).strip()

    # Splitter teksten hvis den inneholder ord som "Leil", "H0..." eller "Leilighet"
    parts = re.split(
        r"\b(leil|h\d+|leilighet)\b", tekst, flags=re.IGNORECASE
    )
    base_adresse = parts[0].strip()

    # Fjerner eventuelle kommaer eller løse tegn helt på slutten etter splittingen
    base_adresse = base_adresse.rstrip(",")
    return base_adresse.strip()


def geokod_adresse(adresse_tekst):
    """Slår opp adresse mot Kartverkets offisielle API."""
    adresse_renset = rens_adresse(adresse_tekst)
    if not adresse_renset:
        return None, None

    url = "https://ws.geonorge.no/adresser/v1/sok"
    parametere = {
        "sok": adresse_renset,
        "kommunenummer": "0301",  # Kun Oslo kommune
    }

    try:
        respons = requests.get(url, params=parametere)
        if respons.status_code == 200:
            data = respons.json()
            adresser = data.get("adresser", [])
            if adresser and len(adresser) > 0:
                forste_treff = adresser[0]
                punkt = forste_treff.get("representasjonspunkt", {})
                return punkt.get("lat"), punkt.get("lon")
    except Exception as e:
        print(f"Feil ved oppslag av '{adresse_renset}': {e}")

    return None, None


# --- HOVEDPROGRAM ---
inn_fil = r"D:\Talefoten\reservasjoner.xlsx"
ut_fil_geojson = r"D:\Talefoten\reservasjoner.geojson"

print(f"Åpner Excel-filen: {inn_fil}")
df = pd.read_excel(inn_fil)

# Oppretter standard GeoJSON-struktur
geojson_data = {"type": "FeatureCollection", "features": []}

print(
    f"Starter geolokalisering av {len(df)} rader (kun 'Adresse' kolonnen)..."
)

for indeks, rad in df.iterrows():
    original_adresse = rad["Adresse"]

    if pd.isna(original_adresse):
        continue

    # Slår opp mot Kartverket
    lat, lon = geokod_adresse(original_adresse)

    if lat and lon:
        # NYTT: Vi lager et helt rent objekt med KUN adressefeltet,
        # slik at vi unngår 'Dato' og andre uønskede kolonner.
        egenskaper = {"Adresse": str(original_adresse).strip()}

        # Lager GeoJSON-objektet (Standard krever [Lengdegrad, Breddegrad])
        feature = {
            "type": "Feature",
            "properties": egenskaper,
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)],
            },
        }

        geojson_data["features"].append(feature)
        print(
            f"[{indeks + 1}/{len(df)}] Suksess: {original_adresse} -> [{lon}, {lat}]"
        )
    else:
        print(
            f"[{indeks + 1}/{len(df)}] Fant ikke koordinater for: {original_adresse}"
        )

    # Kort pause for å unngå overbelastning av serveren
    time.sleep(0.1)

# Skriver datasettet til en strukturert GeoJSON-fil
with open(ut_fil_geojson, "w", encoding="utf-8") as f:
    json.dump(geojson_data, f, ensure_ascii=False, indent=2)

print(f"\nFerdig! GeoJSON-filen er lagret her: {ut_fil_geojson}")
