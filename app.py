import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="Sinefil Tayfa", layout="wide")
st.title("Güvenlik Film İzliyor")

@st.cache_data
def load_data():
    df = pd.read_csv("Guvenlik - Sayfa1.csv")
    
    rating_cols = ['ataberk_rtg', 'batu_rtg', 'ceylin_rtg', 'gokalp_rtg', 'kutay_rtg', 'onur_rtg']
    
    df['Grup Ortalaması'] = df[rating_cols].mean(axis=1).round(2)
    df['Zevk Farkı (Std)'] = df[rating_cols].std(axis=1).round(2)
    df['IMDb (5 Üzerinden)'] = (df['imdb'] / 2).round(2)
    
    return df

df = load_data()

izlenen_filmler = df.dropna(subset=['Grup Ortalaması'])

TMDB_API_KEY = st.secrets["TMDB_API_KEY"]

def get_tmdb_data(film_adi):
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": film_adi,
        "language": "tr-TR"
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    if data["results"]:
        film = data["results"][0]
        poster_path = film.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w300{poster_path}" if poster_path else None
        genres = film.get("genre_ids", [])
        return {
            "poster_url": poster_url,
            "tmdb_rating": round(film.get("vote_average", 0) / 2, 2),  # 10'dan 5'e çevir
            "overview": film.get("overview", ""),
        }
    return None


st.subheader("🏆 Genel Durum")
col1, col2, col3 = st.columns(3)

col1.metric("Toplam İzlenen Film", len(izlenen_filmler))

if not izlenen_filmler.empty:
    en_iyi_idx = izlenen_filmler["Grup Ortalaması"].idxmax()
    col2.metric("Altın Güvenliğin Güncel Sahibi", izlenen_filmler.loc[en_iyi_idx, "film_adi"])
    
    tartismali_filmler = izlenen_filmler.dropna(subset=['Zevk Farkı (Std)'])
    if not tartismali_filmler.empty:
        en_tartismali_idx = tartismali_filmler["Zevk Farkı (Std)"].idxmax()
        col3.metric("En Kaos Yaratan Film", tartismali_filmler.loc[en_tartismali_idx, "film_adi"])
    else:
        col3.metric("En Kaos Yaratan Film", "Yeterli Veri Yok")
else:
    col2.metric("Altın Güvenliğin Güncel Sahibi", "-")
    col3.metric("En Kaos Yaratan Film", "-")

st.markdown("---")

st.subheader("🍿 Film Listesi ve Puanlar")
st.dataframe(df.style.highlight_max(axis=0, subset=["Grup Ortalaması"], color="#2E7D32"))

st.markdown("---")
st.subheader("🎬 Film Kartları")

@st.cache_data
def get_poster(film_adi):
    tmdb = get_tmdb_data(film_adi)
    return tmdb

cols_per_row = 4
filmler = izlenen_filmler.reset_index(drop=True)

for i in range(0, len(filmler), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, col in enumerate(cols):
        if i + j < len(filmler):
            film = filmler.iloc[i + j]
            tmdb = get_poster(film["film_adi"])
            with col:
                if tmdb and tmdb["poster_url"]:
                    st.image(poster_url, width=180)
                else:
                    st.markdown("🎞️ Poster yok")
                st.markdown(f"**{film['film_adi']}**")
                st.markdown(f"_{film['yonetmen']}_")
                st.markdown(f"⭐ Grup: `{film['Grup Ortalaması']}`")
                st.markdown(f"📽️ Öneren: `{film['oneren']}`")
st.subheader("📊 Güvenlik vs. Dünya")
if not izlenen_filmler.empty:
    grafik_verisi = izlenen_filmler.rename(columns={"film_adi": "Film Adı"})
    
    fig = px.bar(
        grafik_verisi,
        y="Film Adı", 
        x=["Grup Ortalaması", "letterboxd_avr", "IMDb (5 Üzerinden)"],
        barmode="group", 
        orientation="h"  
    )
    dinamik_yukseklik = max(400, len(grafik_verisi) * 60)
    fig.update_layout(
        yaxis_title=None, 
        xaxis_title="Puan",
        legend_title="Puan Türü",
        hovermode="y unified",
        height=dinamik_yukseklik
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Grafik oluşturmak için henüz film oylanmamış.")