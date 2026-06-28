import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Sinefil Tayfa", layout="wide")

# ── Sabitler ──────────────────────────────────────────────────────────────────
RATING_COLS = ['ataberk_rtg', 'batu_rtg', 'ceylin_rtg', 'gokalp_rtg', 'kutay_rtg', 'onur_rtg']
ISIMLER     = ['Ataberk', 'Batu', 'Ceylin', 'Gökalp', 'Kutay', 'Onur']
RTG_MAP     = dict(zip(ISIMLER, RATING_COLS))

# ── Veri ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_data():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet  = client.open("Guvenlik").sheet1
    df     = pd.DataFrame(sheet.get_all_records())

    for col in RATING_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['letterboxd_avr']       = pd.to_numeric(df['letterboxd_avr'], errors='coerce')
    df['Grup Ortalaması']      = df[RATING_COLS].mean(axis=1).round(2)
    df['Zevk Farkı (Std)']    = df[RATING_COLS].std(axis=1).round(2)
    df['IMDb (5 Üzerinden)']  = pd.to_numeric(df['imdb'], errors='coerce').div(2).round(2)
    return df

df = load_data()
izlenen_filmler = df.dropna(subset=RATING_COLS).copy()

# ── TMDB ──────────────────────────────────────────────────────────────────────
TMDB_API_KEY = st.secrets["TMDB_API_KEY"]

@st.cache_data(show_spinner=False)
def get_poster(film_adi, yonetmen=None, tmdb_id=None):
    base = "https://api.themoviedb.org/3"
    img  = "https://image.tmdb.org/t/p/w300"

    def parse(film):
        poster_path = film.get("poster_path")
        return {
            "poster_url":  img + poster_path if poster_path else None,
            "tmdb_rating": round(film.get("vote_average", 0) / 2, 2),
            "overview":    film.get("overview", ""),
        }

    try:
        # 1) tmdb_id varsa direkt çek — en güvenilir yol
        if pd.notna(tmdb_id) and str(tmdb_id).strip() and str(tmdb_id).lower() != 'none':
            try:
                temiz_id = int(float(tmdb_id))
                r = requests.get(f"{base}/movie/{temiz_id}",
                                 params={"api_key": TMDB_API_KEY, "language": "tr-TR"}, timeout=5)
                if r.ok:
                    return parse(r.json())
            except ValueError:
                pass # ID sayıya çevrilemezse arama adımlarına geçsin

        # 2) Film adı + yönetmen ile ara
        query = f"{film_adi} {yonetmen}".strip() if yonetmen else film_adi
        r = requests.get(f"{base}/search/movie",
                         params={"api_key": TMDB_API_KEY, "query": query, "language": "tr-TR"},
                         timeout=5)
        if r.ok and r.json()["results"]:
            return parse(r.json()["results"][0])

        # 3) Yönetmenli sorgu sonuç vermezse sadece film adıyla tekrar dene
        if yonetmen:
            r = requests.get(f"{base}/search/movie",
                             params={"api_key": TMDB_API_KEY, "query": film_adi, "language": "tr-TR"},
                             timeout=5)
            if r.ok and r.json()["results"]:
                return parse(r.json()["results"][0])

    except Exception:
        pass
    return None

# ── Sidebar navigasyon ────────────────────────────────────────────────────────
st.sidebar.title("🎬 Güvenlik Film")
sayfa = st.sidebar.radio(
    "Sayfa",
    ["🏠 Genel", "🎬 Film Kartları", "🎯 Sıralama", "😎 En Zevk Sahibi", "📊 Güvenlik vs Dünya", "👤 Profil"],
    label_visibility="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
# SAYFA: GENEL DURUM
# ══════════════════════════════════════════════════════════════════════════════
if sayfa == "🏠 Genel":
    st.title("Güvenlik Film İzliyor")
    st.subheader("🏆 Vaziyet")
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İzlenen Film", len(izlenen_filmler))

    if not izlenen_filmler.empty:
        en_iyi_idx = izlenen_filmler["Grup Ortalaması"].idxmax()
        col2.metric("Altın Güvenliğin Güncel Sahibi", izlenen_filmler.loc[en_iyi_idx, "film_adi"])
        tartismali = izlenen_filmler.dropna(subset=['Zevk Farkı (Std)'])
        if not tartismali.empty:
            col3.metric("En Kaos Yaratan Film",
                        tartismali.loc[tartismali["Zevk Farkı (Std)"].idxmax(), "film_adi"])
        else:
            col3.metric("En Kaos Yaratan Film", "Yeterli Veri Yok")
    else:
        col2.metric("Altın Güvenliğin Güncel Sahibi", "-")
        col3.metric("En Kaos Yaratan Film", "-")

    st.markdown("---")
    st.subheader("🍿 Film Listesi ve Puanlar")
    st.dataframe(df, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# SAYFA: FİLM KARTLARI
# ══════════════════════════════════════════════════════════════════════════════
elif sayfa == "🎬 Film Kartları":
    st.title("🎬 Film Kartları")
    cols_per_row = 4
    filmler      = izlenen_filmler.reset_index(drop=True)

    for i in range(0, len(filmler), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(filmler):
                film = filmler.iloc[i + j]
                tmdb = get_poster(film["film_adi"], yonetmen=film.get("yonetmen"), tmdb_id=film.get("tmdb_id"))
                with col:
                    if tmdb and tmdb["poster_url"]:
                        st.image(tmdb["poster_url"], width=180)
                    else:
                        st.markdown("🎞️ Poster yok")
                    st.markdown(f"**{film['film_adi']}**")
                    st.markdown(f"_{film['yonetmen']}_")
                    st.markdown(f"⭐ Grup: `{film['Grup Ortalaması']}`")
                    st.markdown(f"📽️ Öneren: `{film['oneren']}`")

# ══════════════════════════════════════════════════════════════════════════════
# SAYFA: KİŞİ SIRALAMASI
# ══════════════════════════════════════════════════════════════════════════════
elif sayfa == "🎯 Sıralama":
    st.title("🎯 Kişi Sıralaması")
    kisi_stats = []
    for col, isim in zip(RATING_COLS, ISIMLER):
        kdf = df.dropna(subset=[col])
        if not kdf.empty:
            kisi_stats.append({
                "İsim":           isim,
                "Ortalama Puan":  round(kdf[col].mean(), 2),
                "Grup'tan Sapma": round((kdf[col] - kdf['Grup Ortalaması']).abs().mean(), 2),
            })

    if kisi_stats:
        kisi_df_gosterim = pd.DataFrame(kisi_stats).sort_values("Grup'tan Sapma")
        st.dataframe(kisi_df_gosterim, hide_index=True)

        min_sapma = kisi_df_gosterim["Grup'tan Sapma"].min()
        max_sapma = kisi_df_gosterim["Grup'tan Sapma"].max()
        en_tutarlilar = kisi_df_gosterim[kisi_df_gosterim["Grup'tan Sapma"] == min_sapma]["İsim"].tolist()
        en_aykinlar   = kisi_df_gosterim[kisi_df_gosterim["Grup'tan Sapma"] == max_sapma]["İsim"].tolist()

        col1, col2 = st.columns(2)
        col1.metric("🎖️ Düz İnsan", ", ".join(en_tutarlilar), f"Sapma: {min_sapma}")
        col2.metric("🌪️ Marjinal",  ", ".join(en_aykinlar),   f"Sapma: {max_sapma}")

# ══════════════════════════════════════════════════════════════════════════════
# SAYFA: EN ZEVK SAHİBİ
# ══════════════════════════════════════════════════════════════════════════════
elif sayfa == "😎 En Zevk Sahibi":
    st.title("😎 En Zevk Sahibi")
    if not izlenen_filmler.empty:
        oneren_stats = izlenen_filmler.groupby("oneren").agg(
            Film_Sayisi=("film_adi", "count"),
            Ortalama_Grup_Puani=("Grup Ortalaması", "mean")
        ).round(2).reset_index()
        oneren_stats.columns = ["Öneren", "Önerdiği Film Sayısı", "Ortalama Grup Puanı"]
        oneren_stats = oneren_stats.sort_values("Ortalama Grup Puanı", ascending=False)
        st.dataframe(oneren_stats, hide_index=True)
        max_puan = oneren_stats["Ortalama Grup Puanı"].max()
        en_zevkliler = oneren_stats[oneren_stats["Ortalama Grup Puanı"] == max_puan]["Öneren"].tolist()
        st.metric("🏅 En Zevk Sahibi", ", ".join(en_zevkliler), f"Ort: {max_puan}")
    else:
        st.info("Yeterli veri yok.")

# ══════════════════════════════════════════════════════════════════════════════
# SAYFA: GÜVENLİK VS DÜNYA
# ══════════════════════════════════════════════════════════════════════════════
elif sayfa == "📊 Güvenlik vs Dünya":
    st.title("📊 Güvenlik vs. Dünya")
    if not izlenen_filmler.empty:
        grafik_verisi = izlenen_filmler.rename(columns={
            "film_adi": "Film Adı", 
            "letterboxd_avr": "Letterboxd Ortalaması"
        })
        
        # Dağılım Grafiği (Scatter Plot) oluşturuyoruz
        fig = px.scatter(
            grafik_verisi,
            x="Letterboxd Ortalaması",
            y="Grup Ortalaması",
            hover_name="Film Adı",
            color="Grup Ortalaması",
            color_continuous_scale="RdYlGn", # Kırmızıdan yeşile renk skalası
            size_max=15
        )
        
        # 45 derecelik referans çizgisi (y=x)
        fig.add_shape(
            type="line", line=dict(dash='dash', color="gray"),
            x0=0, y0=0, x1=5, y1=5
        )
        
        fig.update_layout(
            xaxis_title="Dünya (Letterboxd) Puanı",
            yaxis_title="Vaziyet (Grup Ortalaması)",
            height=600,
            hovermode="closest",
            xaxis=dict(range=[0.5, 5.2]),
            yaxis=dict(range=[0.5, 5.2])
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 **Grafik Nasıl Okunur?** Kesik çizginin **üstünde** kalan filmleri dünya ortalamasından daha çok sevmişsiniz. **Altında** kalanlarda ise dünya sizden daha iyimser.")
    else:
        st.info("Grafik oluşturmak için henüz film oylanmamış.")

# ══════════════════════════════════════════════════════════════════════════════
# SAYFA: PROFİL
# ══════════════════════════════════════════════════════════════════════════════
elif sayfa == "👤 Profil":

    # Kişi seçimi
    st.sidebar.markdown("---")
    secili = st.sidebar.selectbox("Kişi seç", ISIMLER, key="profil_kisi")
    rtg_kol = RTG_MAP[secili]

    # Bu kişinin oy verdiği filmler
    kisi_df = df.dropna(subset=[rtg_kol]).copy()
    kisi_df = kisi_df[kisi_df[rtg_kol].notna()].copy()
    kisi_df['sapma'] = kisi_df[rtg_kol] - kisi_df['Grup Ortalaması']
    kisi_df = kisi_df.sort_values(rtg_kol, ascending=False).reset_index(drop=True)

    st.title(f"👤 {secili}'in Profili")

    if kisi_df.empty:
        st.warning(f"{secili} henüz hiç film değerlendirmemiş.")
        st.stop()

    puan_serisi = kisi_df[rtg_kol]

    # ── Özet metrikler ──
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("İzlenen Film",    len(puan_serisi))
    m2.metric("Ortalama Puan",   f"{puan_serisi.mean():.2f}")
    m3.metric("En Yüksek",       f"{puan_serisi.max():.1f}")
    m4.metric("En Düşük",        f"{puan_serisi.min():.1f}")
    # Önerdiği filmler kaçı?
    onerdigi_sayi = len(df[df['oneren'].str.lower() == secili.lower()])
    m5.metric("Önerdiği Film",   onerdigi_sayi)

    st.markdown("---")

    # ── En sevdiği 5 film ──
    st.subheader("❤️ En Çok Sevdiği Filmler")
    en_iyi = kisi_df.head(5)
    cols   = st.columns(len(en_iyi))
    for col, (_, row) in zip(cols, en_iyi.iterrows()):
        tmdb = get_poster(row['film_adi'], yonetmen=row.get('yonetmen'), tmdb_id=row.get('tmdb_id'))
        with col:
            if tmdb and tmdb["poster_url"]:
                st.image(tmdb["poster_url"], width=130)
            else:
                st.markdown("🎞️")
            puan = row[rtg_kol]
            renk = "#2ecc71" if puan >= 7 else "#e67e22" if puan >= 5 else "#e74c3c"
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='background:{renk};color:white;border-radius:10px;"
                f"padding:2px 8px;font-size:13px;font-weight:700'>★ {puan}</span></div>",
                unsafe_allow_html=True
            )
            isim = row['film_adi']
            st.caption(isim[:20] + "…" if len(isim) > 20 else isim)

    st.markdown("---")

    # ── En az sevdiği 5 film ──
    st.subheader("💔 En Az Sevdiği Filmler")
    en_kotu = kisi_df.tail(5).sort_values(rtg_kol)
    cols    = st.columns(len(en_kotu))
    for col, (_, row) in zip(cols, en_kotu.iterrows()):
        tmdb = get_poster(row['film_adi'], yonetmen=row.get('yonetmen'), tmdb_id=row.get('tmdb_id'))
        with col:
            if tmdb and tmdb["poster_url"]:
                st.image(tmdb["poster_url"], width=130)
            else:
                st.markdown("🎞️")
            puan = row[rtg_kol]
            renk = "#2ecc71" if puan >= 7 else "#e67e22" if puan >= 5 else "#e74c3c"
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='background:{renk};color:white;border-radius:10px;"
                f"padding:2px 8px;font-size:13px;font-weight:700'>★ {puan}</span></div>",
                unsafe_allow_html=True
            )
            isim = row['film_adi']
            st.caption(isim[:20] + "…" if len(isim) > 20 else isim)

    st.markdown("---")

    # ── Puan dağılımı ──
    st.subheader("📊 Puan Dağılımı")
    sayimlar = (
        puan_serisi.dropna()
        .round(0).astype(int)
        .value_counts().sort_index()
        .reset_index()
    )
    sayimlar.columns = ["Puan", "Film Sayısı"]
    sayimlar["Puan"] = sayimlar["Puan"].astype(str)

    fig_dagılım = px.bar(
        sayimlar, x="Puan", y="Film Sayısı",
        color_discrete_sequence=["#6c63ff"],
        text="Film Sayısı"
    )
    fig_dagılım.update_layout(
        xaxis_title="Puan", yaxis_title="Film Sayısı",
        showlegend=False, height=300,
        margin=dict(t=20, b=20)
    )
    fig_dagılım.update_traces(textposition="outside")
    st.plotly_chart(fig_dagılım, use_container_width=True)

    st.markdown("---")

    # ── Gruptan sapmalar ──
    st.subheader("🔀 Grup'tan Sapmaları")
    sapma_df = kisi_df[['film_adi', rtg_kol, 'Grup Ortalaması', 'sapma']].copy()
    sapma_df.columns = ["Film", "Puan", "Grup Ort.", "Sapma"]
    sapma_df["Film"] = sapma_df["Film"].apply(lambda x: x[:30] + "…" if len(str(x)) > 30 else x)

    scol1, scol2 = st.columns(2)
    with scol1:
        st.markdown("**📈 Gruptan fazla sevdiklerin**")
        ust = sapma_df.nlargest(5, "Sapma")
        st.dataframe(
            ust.style.format({"Puan": "{:.1f}", "Grup Ort.": "{:.1f}", "Sapma": "+{:.1f}"}),
            hide_index=True, use_container_width=True
        )
    with scol2:
        st.markdown("**📉 Gruptan az sevdiklerin**")
        alt = sapma_df.nsmallest(5, "Sapma")
        st.dataframe(
            alt.style.format({"Puan": "{:.1f}", "Grup Ort.": "{:.1f}", "Sapma": "{:.1f}"}),
            hide_index=True, use_container_width=True
        )

    st.markdown("---")

    # ── Önerdiği filmler ──
    onerdigi_df = df[df['oneren'].str.strip().str.lower() == secili.lower()].copy()
    if not onerdigi_df.empty:
        st.subheader(f"🎯 {secili}'in Önerdiği Filmler")
        onerdigi_df['Grup Ortalaması'] = onerdigi_df[RATING_COLS].mean(axis=1).round(2)

        cols = st.columns(min(len(onerdigi_df), 5))
        for col, (_, row) in zip(cols, onerdigi_df.head(5).iterrows()):
            tmdb = get_poster(row['film_adi'], yonetmen=row.get('yonetmen'), tmdb_id=row.get('tmdb_id'))
            with col:
                if tmdb and tmdb["poster_url"]:
                    st.image(tmdb["poster_url"], width=130)
                else:
                    st.markdown("🎞️")
                puan = row.get('Grup Ortalaması', None)
                if pd.notna(puan):
                    renk = "#2ecc71" if puan >= 7 else "#e67e22" if puan >= 5 else "#e74c3c"
                    st.markdown(
                        f"<div style='text-align:center'>"
                        f"<span style='background:{renk};color:white;border-radius:10px;"
                        f"padding:2px 8px;font-size:13px;font-weight:700'>★ {puan}</span></div>",
                        unsafe_allow_html=True
                    )
                isim = row['film_adi']
                st.caption(isim[:20] + "…" if len(isim) > 20 else isim)

        ort = onerdigi_df['Grup Ortalaması'].mean()
        st.caption(f"Önerdiği filmlerin grup ortalaması: **{ort:.2f}**")

    # ── Tüm puanlar tablosu ──
    with st.expander("📋 Tüm Puanlar"):
        tablo = kisi_df[['film_adi', rtg_kol, 'Grup Ortalaması', 'sapma']].copy()
        tablo.columns = ["Film", "Puan", "Grup Ort.", "Sapma"]
        st.dataframe(
            tablo.style
                 .format({"Puan": "{:.1f}", "Grup Ort.": "{:.1f}", "Sapma": "{:+.1f}"}),
            hide_index=True, use_container_width=True
        )