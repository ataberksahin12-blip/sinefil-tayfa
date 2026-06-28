import streamlit as st
import pandas as pd

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

st.subheader("📊 Güvenlik vs. Dünya")
if not izlenen_filmler.empty:
        st.bar_chart(
        izlenen_filmler,
        x="film_adi", 
        y=["Grup Ortalaması", "letterboxd_avr", "IMDb (5 Üzerinden)"] 
        )
else:
    st.info("Grafik oluşturmak için henüz film oylanmamış.")