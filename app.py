import os, io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Netflix Originals — Veri Analizi", layout="wide")
st.title("📺 Netflix Originals — Veri Analizi (CSV)")
st.caption("CSV yükle → Filtrele → Etkileşimli grafiklere bak → Kısa raporu indir")

ENCODINGS = ["utf-8", "utf-8-sig", "cp1254", "latin1"]
SEPS = [None, ",", ";", "\t"]  

def _read_csv_path(path: str) -> pd.DataFrame:
    last_err = None
    for enc in ENCODINGS:
        for sep in SEPS:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, engine="python", on_bad_lines="skip")
                df.columns = [c.strip() for c in df.columns]
                return df
            except Exception as e:
                last_err = e
                continue
    raise RuntimeError(f"CSV okunamadı: {last_err}")

def _read_csv_bytes(b: bytes) -> pd.DataFrame:
    last_err = None
    for enc in ENCODINGS:
        try:
            s = b.decode(enc)
            df = pd.read_csv(io.StringIO(s), sep=None, engine="python", on_bad_lines="skip")
            df.columns = [c.strip() for c in df.columns]
            return df
        except Exception as e:
            last_err = e
            continue
            
    for sep in SEPS[1:]:
        try:
            df = pd.read_csv(io.BytesIO(b), encoding=None, sep=sep, engine="python", on_bad_lines="skip")
            df.columns = [c.strip() for c in df.columns]
            return df
        except Exception as e:
            last_err = e
            continue
            
    raise RuntimeError(f"Yüklenen CSV okunamadı: {last_err}")

def parse_premiere(df: pd.DataFrame) -> pd.DataFrame:
    if "Premiere" in df.columns:
        df["Premiere_dt"]  = pd.to_datetime(df["Premiere"], format="%d-%b-%y", errors="coerce")
        df["PremiereYear"] = df["Premiere_dt"].dt.year
    return df

def build_genres(df: pd.DataFrame) -> pd.DataFrame:
    col_to_use = None
    if "GenreLabels" in df.columns:
        col_to_use = "GenreLabels"
    elif "Genre" in df.columns:
        col_to_use = "Genre"
        
    if col_to_use:
        df["GenresList"] = df[col_to_use].astype(str).str.replace('"', '') \
                                             .str.replace(r'[/&]| and ', ',', regex=True) \
                                             .str.lower() \
                                             .str.split(',')
    return df

def compute_episode_length(df: pd.DataFrame) -> pd.DataFrame:
    avg_col = "EpisodeLengthAvg"
    df[avg_col] = np.nan
   
    if {"MinLength", "MaxLength"}.issubset(df.columns):
        min_len = pd.to_numeric(df["MinLength"], errors="coerce")
        max_len = pd.to_numeric(df["MaxLength"], errors="coerce")
        valid_mask = (min_len > 0) & (max_len > 0) & (min_len.notna()) & (max_len.notna())
        df.loc[valid_mask, avg_col] = (min_len[valid_mask] + max_len[valid_mask]) / 2
    
    if "Length" in df.columns:
        missing_mask = df[avg_col].isna()
        if missing_mask.any():
            ranges = df.loc[missing_mask, "Length"].astype(str).str.extract(r'(\d+)[–-](\d+)')
            singles = df.loc[missing_mask, "Length"].astype(str).str.extract(r'(\d+)\s+min')

            r1 = pd.to_numeric(ranges[0], errors="coerce")
            r2 = pd.to_numeric(ranges[1], errors="coerce")
            s1 = pd.to_numeric(singles[0], errors="coerce")

            range_avg = (r1 + r2) / 2
            
            df.loc[missing_mask, 'LengthAvg_fromText'] = range_avg.fillna(s1)
            df[avg_col] = df[avg_col].fillna(df['LengthAvg_fromText'])
            
    df.loc[df[avg_col] <= 0, avg_col] = np.nan
    return df

def short_report(by_year: pd.DataFrame, top_genres: pd.Series, df: pd.DataFrame) -> str:
    lines = []
    
    if by_year is not None and not by_year.empty:
        first = int(by_year["PremiereYear"].min())
        last  = int(by_year["PremiereYear"].max())
        lines.append(f"Veri Aralığı: {first}-{last}")
        
        last_total = int(by_year[by_year["PremiereYear"]==last]["Count"].sum())
        lines.append(f"Son Yıl ({last}): {last_total} içerik")
        
        total = int(by_year["Count"].sum())
        lines.append(f"Toplam (Filtreli): {total} içerik")
        
    if top_genres is not None and not top_genres.empty:
        lines.append(f"Popüler Tür: {top_genres.index[0]} ({int(top_genres.iloc[0])} adet)")
        
    if "EpisodeLengthAvg" in df.columns:
        avg_len = df["EpisodeLengthAvg"].mean()
        if pd.notna(avg_len):
            lines.append(f"Ort. Bölüm Süresi: {avg_len:.0f} dk")
            
    return "\n".join(lines)

@st.cache_data
def load_data(source_type: str, file_path: str = None, uploaded_file = None):
    try:
        if source_type == "local":
            if not os.path.exists(file_path):
                st.error(f"Varsayılan CSV dosyası bulunamadı: {file_path}")
                return pd.DataFrame()
            df = _read_csv_path(file_path)
        elif source_type == "upload" and uploaded_file:
            df = _read_csv_bytes(uploaded_file.getvalue())
        else:
            return pd.DataFrame()
        
        if "Title" not in df.columns or "Premiere" not in df.columns:
            st.error("CSV dosyası beklenen yapıda değil. 'Title' ve 'Premiere' sütunları zorunludur.")
            return pd.DataFrame()

        df = parse_premiere(df)
        df = build_genres(df)
        df = compute_episode_length(df)
        return df
    
    except Exception as e:
        st.error(f"Veri yüklenirken kritik bir hata oluştu: {e}")
        return pd.DataFrame()

st.sidebar.title("Filtreler")

default_csv = "NetflixOriginals.csv"
use_default_initial = os.path.exists(default_csv)
use_default = st.sidebar.checkbox(f"`{default_csv}` kullan", value=use_default_initial)
uploaded_file = st.sidebar.file_uploader("Veya 📄 CSV Yükle", type=["csv"])

df = pd.DataFrame()
if use_default and not uploaded_file:
    df = load_data("local", file_path=default_csv)
elif uploaded_file:
    df = load_data("upload", uploaded_file=uploaded_file)
else:
    st.info("Lütfen bir CSV dosyası yükleyin veya yerel dosyayı kullanın.")
    st.stop()

if df.empty:
    st.stop()
    
dff = df.copy()

if "PremiereYear" in dff.columns and dff["PremiereYear"].notna().any():
    min_year = int(dff["PremiereYear"].min())
    max_year = int(dff["PremiereYear"].max())
    
    selected_years = st.sidebar.slider(
        "📅 Yıl Aralığı (Premiere)",
        min_year, max_year,
        (min_year, max_year)
    )
    dff = dff[
        (dff["PremiereYear"] >= selected_years[0]) &
        (dff["PremiereYear"] <= selected_years[1])
    ]
else:
    st.sidebar.warning("Yıl filtresi için 'PremiereYear' sütunu bulunamadı.")

if "Table" in dff.columns:
    tables = dff["Table"].dropna().unique()
    if len(tables) > 1:
        selected_tables = st.sidebar.multiselect(
            "📦 Kategori (Table)",
            options=tables,
            default=tables
        )
        dff = dff[dff["Table"].isin(selected_tables)]

if "Language" in dff.columns:
    langs = dff["Language"].dropna().unique()
    if len(langs) > 1:
        top_langs = dff["Language"].value_counts().head(20).index.tolist()
        
        selected_langs = st.sidebar.multiselect(
            " Dil (Popüler 20)",
            options=top_langs,
            default=top_langs
        )
        dff = dff[dff["Language"].isin(selected_langs)]

top_n_genres = 10
if "GenresList" in dff.columns:
    ex = dff.explode("GenresList")
    ex["GenresList"] = ex["GenresList"].str.strip()
    
    ex = ex[ex["GenresList"].notna() & (ex["GenresList"] != "") & (ex["GenresList"] != "nan")]
    
    if not ex.empty:
        top_n_genres = st.sidebar.slider(
            "🏷️ Top N Tür Sayısı",
            min_value=3, max_value=20, value=10, step=1
        )
else:
    ex = pd.DataFrame() 

if dff.empty:
    st.warning("Filtrelere uyan hiçbir veri bulunamadı.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    " Yıla Göre Adet", 
    " Popüler Türler", 
    " Durum ", 
    " Bölüm Uzunluğu", 
    " Sezon vs Bölüm"
])

with tab1:
    if "PremiereYear" in dff.columns:
        by_year = dff.groupby("PremiereYear")["Title"].count().reset_index()
        by_year.columns = ["PremiereYear", "Count"]
        
        fig1 = px.line(by_year, x="PremiereYear", y="Count", 
                       title="Yıllara Göre Yayınlanan İçerik Sayısı",
                       markers=True)
        fig1.update_xaxes(title="Yayın Yılı")
        fig1.update_yaxes(title="İçerik Sayısı")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Yıl grafiği için 'PremiereYear' sütunu eksik.")
        by_year = pd.DataFrame() 

with tab2:
    if not ex.empty:
        topg = ex["GenresList"].value_counts().head(top_n_genres)
        fig2 = px.bar(topg, y=topg.index, x=topg.values,
                      orientation='h',
                      title=f"En Popüler {top_n_genres} Tür")
        fig2.update_layout(xaxis_title="İçerik Sayısı", yaxis_title="Tür", yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Tür grafiği için 'GenresList' sütunu oluşturulamadı ('Genre' veya 'GenreLabels' eksik).")
        topg = pd.Series([],dtype=int) 

with tab3:
    if "Status" in dff.columns:
        status_norm = dff["Status"].astype(str).str.lower()
        status_map = {
            "renewed": "Renewed",
            "ended": "Ended",
            "miniseries": "Miniseries",
            "pending": "Pending",
            "tbd": "Pending"
        }
        dff["StatusNorm"] = "Other"
        for key, val in status_map.items():
            dff.loc[status_norm.str.contains(key, na=False), "StatusNorm"] = val
            
        status_counts = dff["StatusNorm"].value_counts()
        
        fig3 = px.pie(status_counts, values=status_counts.values, names=status_counts.index,
                      title="İçerik Durumu Dağılımı", hole=0.3)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Durum grafiği için 'Status' sütunu eksik.")

with tab4:
    if {"EpisodeLengthAvg", "Table"}.issubset(dff.columns):
        valid_len_df = dff.dropna(subset=["EpisodeLengthAvg", "Table"])
        if not valid_len_df.empty:
            fig4 = px.box(valid_len_df, x="Table", y="EpisodeLengthAvg",
                          title="Kategorilere Göre Bölüm Uzunlukları (Ortalama)",
                          points="all")
            fig4.update_layout(xaxis_title="Kategori (Table)", yaxis_title="Ortalama Bölüm Uzunluğu (dk)")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Bölüm uzunluğu hesaplanamadı.")
    else:
        st.info("Gerekli kolonlar (EpisodeLengthAvg, Table) bulunamadı.")

with tab5:
    if {"SeasonsParsed","EpisodesParsed"}.issubset(dff.columns):
        s = dff.dropna(subset=["SeasonsParsed","EpisodesParsed"])
        s = s[(s["SeasonsParsed"]>0) & (s["EpisodesParsed"]>0)]
        if not s.empty:
            fig5 = px.scatter(s, x="SeasonsParsed", y="EpisodesParsed", trendline=None,
                              title="Sezon Sayısı vs Bölüm Sayısı", opacity=0.6,
                              hover_name="Title")
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Geçerli sezon/bölüm verisi yok.")
    else:
        st.info("SeasonsParsed / EpisodesParsed kolonları eksik.")

report_text = short_report(by_year, topg.sort_values(ascending=False) if not ex.empty else pd.Series([],dtype=int), dff)

st.sidebar.download_button(
    label=" Kısa Raporu İndir (.txt)",
    data=report_text,
    file_name="netflix_ozet_rapor.txt",
    mime="text/plain"
)

st.subheader("🔎 Filtrelenmiş Veri Önizlemesi (İlk 50)")
st.dataframe(dff.head(50))