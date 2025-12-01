import streamlit as st
import pandas as pd
import os
import glob
import re
import requests
from bs4 import BeautifulSoup

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Fanta-Manager 2026", layout="wide")

FILE_DATABASE = 'fanta_database.csv'
FILE_HISTORY = 'fanta_history.csv'
FILE_ROSE_IMPORT = 'Rose_fantawotblitz.xlsx' 
FILE_CLASSIFICA = 'Classifica_Campionato.xlsx'
FILE_CALENDARIO = 'Calendario_Campionato.xlsx'
DIR_VOTI = 'Voti'
DIR_IMG = 'img'
DIR_LOGO = 'logo'

# --- 1. FUNZIONI DI UTILITÀ ---

def normalizza_nome(nome):
    if pd.isna(nome): return ""
    return str(nome).lower().strip().replace(".", "").replace("'", "")

def normalizza_per_confronto_web(nome):
    if pd.isna(nome): return ""
    n = str(nome).lower().strip().replace(".", "").replace("'", "")
    parole = n.split()
    return parole[-1] if len(parole) > 0 else n

def trova_immagine(nome_giocatore):
    if not os.path.exists(DIR_IMG): return None
    files = os.listdir(DIR_IMG)
    nome_clean = normalizza_nome(nome_giocatore)
    for f in files:
        if normalizza_nome(f.split('.')[0]) == nome_clean: return os.path.join(DIR_IMG, f)
    parole_nome = nome_clean.split()
    for f in files:
        if any(p in normalizza_nome(f.split('.')[0]) for p in parole_nome if len(p) > 3): 
            return os.path.join(DIR_IMG, f)
    return None

def trova_logo(nome_squadra):
    if not os.path.exists(DIR_LOGO): return None
    files = os.listdir(DIR_LOGO)
    if pd.isna(nome_squadra): return None
    nome_clean = normalizza_nome(nome_squadra)
    for f in files:
        if normalizza_nome(f.split('.')[0]) == nome_clean: return os.path.join(DIR_LOGO, f)
    for f in files:
        if nome_clean in normalizza_nome(f.split('.')[0]): return os.path.join(DIR_LOGO, f)
    return None

def estrai_numero_giornata(filepath):
    nome_file = os.path.basename(filepath)
    match = re.search(r'Giornata_(\d+)', nome_file)
    if match: return int(match.group(1))
    return 0

def check_database_integrity(df):
    cols_float = ['Media_Voto', 'Fanta_Media']
    cols_int = ['Gol_Totali', 'Gol_Subiti', 'Partite_Giocate', 'Assist', 
                'Ammonizioni', 'Espulsioni', 'Rigori_Segnati', 'Rigori_Sbagliati', 
                'Rigori_Parati', 'Autoreti']
    if 'Status_Probabile' not in df.columns: df['Status_Probabile'] = '?'
    if df.empty: return df
    for col in cols_float:
        if col not in df.columns: df[col] = 0.0
    for col in cols_int:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df

def get_role_color(ruolo):
    colors = {'P': '#f39c12', 'D': '#27ae60', 'C': '#2980b9', 'A': '#c0392b'}
    return colors.get(ruolo, 'black')

def applica_stile_ruoli(val):
    return f'color: {get_role_color(val)}; font-weight: bold'

# --- SCRAPING GAZZETTA (FILTRO AVANZATO) ---
@st.cache_data(ttl=3600)
def scarica_probabili_formazioni():
    url = "https://www.gazzetta.it/Calcio/prob_form/"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Prendo il testo
            full_text = soup.get_text().lower()
            
            # --- PULIZIA DEL TESTO ---
            # Rimuoviamo tutto ciò che segue parole chiave "pericolose" per ogni blocco partita
            # Siccome il testo è tutto unito, proviamo a rimuovere le sezioni note di "non titolarità"
            
            # Parole che indicano liste di NON titolari
            bad_words = ["indisponibili", "squalificati", "ballottaggi", "panchina", "diffidati", "disposizione in campo"]
            
            # Sostituiamo queste sezioni con spazio vuoto
            # Regex: cerca la parola chiave e prendi i successivi 100 caratteri (o fino a punto)
            # Metodo più aggressivo: Splittiamo il testo e teniamo solo i pezzi "buoni"
            # Ma essendo un blocco unico è rischioso.
            
            # Metodo Euristico: Sostituisco "indisponibili: nome, nome" con "..."
            for word in bad_words:
                # Cerca la parola chiave seguita da testo fino a un punto o a capo
                full_text = re.sub(rf"{word}.*?(\.|\n|$)", "", full_text, flags=re.DOTALL)
            
            return full_text
    except: pass
    return ""

def verifica_titolare(nome, text):
    if not text: return "⚪"
    cog = normalizza_per_confronto_web(nome)
    
    # Se il cognome è molto corto o comune, cerca anche il nome
    if len(cog) < 3:
        # Se è troppo corto rischio falsi positivi, meglio grigio se non siamo sicuri
        return "⚪"
        
    return "🟢" if cog in text else "⚪"

# --- LETTURA FILE ---
def leggi_excel_intelligente(filepath):
    try:
        if filepath.endswith('.csv'):
            df_preview = pd.read_csv(filepath, header=None, nrows=10, encoding='latin1', sep=None, engine='python')
        else:
            df_preview = pd.read_excel(filepath, header=None, nrows=10)
        
        header_row_idx = -1
        for idx, row in df_preview.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            if any(x in row_str for x in ['calciatore', 'nome', 'pos', 'squadra']):
                header_row_idx = idx
                break
        
        if filepath.endswith('.csv'):
            if header_row_idx != -1:
                return pd.read_csv(filepath, header=header_row_idx, encoding='latin1', sep=None, engine='python')
            else:
                return pd.read_csv(filepath, encoding='latin1', sep=None, engine='python')
        else:
            if header_row_idx != -1:
                return pd.read_excel(filepath, header=header_row_idx)
            else:
                return pd.read_excel(filepath)
    except Exception: return None

# --- PARSER CALENDARIO ---
def parse_calendario_complesso(filepath):
    try:
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, header=None, encoding='latin1', sep=None, engine='python')
        else:
            df = pd.read_excel(filepath, header=None)
        
        matches = []
        rows, cols = df.shape
        
        for r in range(rows):
            for c in range(cols):
                cell_val = str(df.iat[r, c]).lower()
                if "giornata lega" in cell_val:
                    try:
                        g_lega = int(re.search(r'(\d+)', cell_val).group(1))
                        g_seriea = "?"
                        if c+2 < cols:
                            s_str = str(df.iat[r, c+2]).lower()
                            if "serie a" in s_str:
                                found = re.search(r'(\d+)', s_str)
                                if found: g_seriea = found.group(1)
                        
                        curr = r + 1
                        while curr < rows:
                            home = df.iat[curr, c]
                            if pd.isna(home) or "giornata" in str(home).lower(): break
                            pt_h = df.iat[curr, c+1]
                            pt_a = df.iat[curr, c+2]
                            away = df.iat[curr, c+3]
                            res = df.iat[curr, c+4]
                            
                            matches.append({
                                'Giornata_Lega': g_lega, 'Giornata_SerieA': g_seriea,
                                'Casa': home, 'Punti_Casa': pt_h,
                                'Punti_Trasferta': pt_a, 'Trasferta': away, 'Risultato': res
                            })
                            curr += 1
                    except: continue
        return pd.DataFrame(matches).sort_values('Giornata_Lega') if matches else None
    except: return None

def get_table_config():
    return {
        "Fanta_Media": st.column_config.ProgressColumn("FM", min_value=5, max_value=10, format="%.2f"),
        "Media_Voto": st.column_config.NumberColumn("MV", format="%.2f"),
        "Gol_Totali": st.column_config.NumberColumn("Gol", format="%d"),
        "Gol_Subiti": st.column_config.NumberColumn("Subiti", format="%d"),
        "Assist": st.column_config.NumberColumn("Ass", format="%d"),
        "Ammonizioni": st.column_config.NumberColumn("Gialli", format="%d"),
        "Espulsioni": st.column_config.NumberColumn("Rossi", format="%d"),
        "Rigori_Parati": st.column_config.NumberColumn("Rig.Par", format="%d"),
        "Rigori_Segnati": st.column_config.NumberColumn("Rig.Fatti", format="%d"),
        "Rigori_Sbagliati": st.column_config.NumberColumn("Rig.Sba", format="%d"),
        "Partite_Giocate": st.column_config.NumberColumn("Pres", format="%d"),
        "Pos": st.column_config.NumberColumn("Rank", format="#%d"),
        "Status_Probabile": st.column_config.TextColumn("News", width="small")
    }

# --- 2. IMPORTA ROSE ---
def importa_rose(filepath):
    try:
        df = leggi_excel_intelligente(filepath)
        if df is None: return None
        if 'Ruolo' not in df.columns: df = pd.read_excel(filepath, header=None)

        players = []
        for col in range(len(df.columns)):
            rows = df.index[df[col].astype(str) == 'Ruolo'].tolist()
            for r in rows:
                team = df.iloc[r-1, col]
                if pd.isna(team): continue
                curr = r + 1
                while curr < len(df):
                    ruolo = df.iloc[curr, col]
                    nome = df.iloc[curr, col+1]
                    serie_a = df.iloc[curr, col+2]
                    costo = df.iloc[curr, col+3]
                    if pd.isna(ruolo) or str(ruolo).startswith("Crediti"): break
                    if pd.notna(nome):
                        p = {
                            'Giocatore': nome, 'Ruolo': ruolo, 
                            'Squadra_SerieA': serie_a, 'Fanta_Squadra': team, 
                            'Costo': costo, 'Media_Voto': 0.0, 'Fanta_Media': 0.0, 
                            'Partite_Giocate': 0, 'Gol_Totali': 0, 'Gol_Subiti': 0, 
                            'Assist': 0, 'Ammonizioni': 0, 'Espulsioni': 0,
                            'Rigori_Segnati': 0, 'Rigori_Sbagliati': 0, 
                            'Rigori_Parati': 0, 'Autoreti': 0, 'Status_Probabile': '?'
                        }
                        players.append(p)
                    curr += 1
        return pd.DataFrame(players)
    except Exception as e:
        st.error(f"Errore lettura Rose: {e}")
        return None

# --- 3. ELABORA VOTI ---
def elabora_storico_voti(df_rose, directory):
    pattern = os.path.join(directory, "*Giornata*.xlsx")
    files = glob.glob(pattern)
    files.sort(key=estrai_numero_giornata)
    
    st.info(f"Elaborazione in corso... File trovati: {len(files)}")
    bar = st.progress(0)
    all_data = []
    history_records = []

    for i, file in enumerate(files):
        giornata_num = estrai_numero_giornata(file)
        try:
            df_day = leggi_excel_intelligente(file)
            if df_day is None: continue
            df_day.columns = df_day.columns.astype(str).str.lower().str.strip()
            cols = df_day.columns
            
            c_nome = next((c for c in cols if c in ['nome', 'calciatore', 'nome calciatore']), None)
            c_voto = next((c for c in cols if c in ['voto', 'v']), None)
            if not c_nome or not c_voto: continue

            c_gf = next((c for c in cols if c == 'gf'), None)
            c_gs = next((c for c in cols if c == 'gs'), None)
            c_rp = next((c for c in cols if c == 'rp'), None)
            c_rs = next((c for c in cols if c == 'rs'), None) 
            c_rf = next((c for c in cols if c == 'rf'), None)
            c_au = next((c for c in cols if c == 'au'), None)
            c_amm = next((c for c in cols if c == 'amm'), None)
            c_esp = next((c for c in cols if c == 'esp'), None)
            c_ass = next((c for c in cols if c == 'ass'), None)

            df_day = df_day.dropna(subset=[c_nome])
            df_day[c_voto] = pd.to_numeric(df_day[c_voto], errors='coerce')
            validi = df_day[df_day[c_voto] > 0].copy()
            validi['clean_name'] = validi[c_nome].apply(normalizza_nome)
            
            def get_val(df_in, col_name):
                if col_name: return pd.to_numeric(df_in[col_name], errors='coerce').fillna(0)
                return 0

            validi['gf'] = get_val(validi, c_gf)
            validi['gs'] = get_val(validi, c_gs)
            validi['rp'] = get_val(validi, c_rp)
            validi['rs'] = get_val(validi, c_rs) 
            validi['rf'] = get_val(validi, c_rf) 
            validi['au'] = get_val(validi, c_au)
            validi['amm'] = get_val(validi, c_amm)
            validi['esp'] = get_val(validi, c_esp)
            validi['ass'] = get_val(validi, c_ass)

            validi['fantavoto'] = (validi[c_voto] 
                                + (validi['gf']*3) + (validi['rf']*3) + (validi['rp']*3) + (validi['ass']*1)
                                - (validi['gs']*1) - (validi['au']*2) - (validi['rs']*3) 
                                - (validi['amm']*0.5) - (validi['esp']*1))
            
            mini = validi[['clean_name', c_voto, 'fantavoto', 'gf', 'gs', 'rp', 'rs', 'rf', 'au', 'amm', 'esp', 'ass']].rename(columns={c_voto: 'voto'})
            all_data.append(mini)
            
            hist_mini = validi[['clean_name', c_voto, 'fantavoto']].copy()
            hist_mini['Giornata'] = giornata_num
            hist_mini.rename(columns={c_voto: 'Voto', 'fantavoto': 'Fantavoto'}, inplace=True)
            history_records.append(hist_mini)

        except Exception: pass
        bar.progress((i + 1) / len(files))

    if history_records: pd.concat(history_records).to_csv(FILE_HISTORY, index=False)

    if all_data:
        big_df = pd.concat(all_data)
        stats = big_df.groupby('clean_name').sum(numeric_only=True)
        stats['presenze'] = big_df.groupby('clean_name')['voto'].count()
        stats['media_voto'] = big_df.groupby('clean_name')['voto'].mean()
        stats['fanta_media'] = big_df.groupby('clean_name')['fantavoto'].mean()
        
        df_rose = check_database_integrity(df_rose)
        count = 0
        for idx, row in df_rose.iterrows():
            nk = normalizza_nome(row['Giocatore'])
            if nk in stats.index:
                s = stats.loc[nk]
                df_rose.at[idx, 'Media_Voto'] = s['media_voto']
                df_rose.at[idx, 'Fanta_Media'] = s['fanta_media']
                df_rose.at[idx, 'Partite_Giocate'] = int(s['presenze'])
                df_rose.at[idx, 'Gol_Totali'] = int(s['gf'])
                df_rose.at[idx, 'Gol_Subiti'] = int(s['gs'])
                df_rose.at[idx, 'Assist'] = int(s['ass'])
                df_rose.at[idx, 'Ammonizioni'] = int(s['amm'])
                df_rose.at[idx, 'Espulsioni'] = int(s['esp'])
                df_rose.at[idx, 'Rigori_Segnati'] = int(s['rf']) 
                df_rose.at[idx, 'Rigori_Sbagliati'] = int(s['rs']) 
                df_rose.at[idx, 'Rigori_Parati'] = int(s['rp'])
                df_rose.at[idx, 'Autoreti'] = int(s['au'])
                count += 1
        return df_rose
    return df_rose

# --- MAIN EXECUTION ---
if os.path.exists(FILE_DATABASE):
    df = pd.read_csv(FILE_DATABASE)
    df = check_database_integrity(df)
else:
    df = pd.DataFrame()

st.title("⚽ Fanta-Manager 2026")

# SIDEBAR
st.sidebar.header("Pannello Controllo")
if st.sidebar.button("🔄 Ricarica Rose (Reset)"):
    if os.path.exists(FILE_ROSE_IMPORT):
        nuovo = importa_rose(FILE_ROSE_IMPORT)
        if nuovo is not None:
            nuovo.to_csv(FILE_DATABASE, index=False)
            st.rerun()

if st.sidebar.button("📊 Aggiorna Storico Voti"):
    if os.path.exists(DIR_VOTI):
        df = elabora_storico_voti(df, DIR_VOTI)
        df.to_csv(FILE_DATABASE, index=False)
        st.rerun()

st.sidebar.markdown("### 🌐 Probabili Formazioni")
if st.sidebar.button("📡 Scarica da Gazzetta.it"):
    with st.spinner("Scraping Gazzetta in corso..."):
        text_probabili = scarica_probabili_formazioni()
        if text_probabili:
            df['Status_Probabile'] = df['Giocatore'].apply(lambda x: verifica_titolare(x, text_probabili))
            df.to_csv(FILE_DATABASE, index=False)
            st.success("Fatto! Controlla la colonna 'News'.")
            st.rerun()
        else:
            st.warning("Impossibile scaricare le formazioni. Riprova più tardi.")

if not df.empty and df['Partite_Giocate'].sum() > 0:

    # --- 1. ULTIMA GIORNATA (LAYOUT 2x2 GRIGLIA) ---
    if os.path.exists(FILE_CALENDARIO):
        df_cal = parse_calendario_complesso(FILE_CALENDARIO)
        if df_cal is not None:
            giocate = df_cal[df_cal['Risultato'].astype(str).str.contains(r'\d', na=False)]
            
            if not giocate.empty:
                last_g = giocate['Giornata_Lega'].max()
                matches_last = giocate[giocate['Giornata_Lega'] == last_g]
                
                st.markdown(f"##### 🏟️ Ultimo Turno: Giornata {last_g}")
                
                # GRIGLIA 2 per riga (2x2)
                rows_iter = [matches_last.iloc[i:i+2] for i in range(0, len(matches_last), 2)]
                
                for row_matches in rows_iter:
                    cols = st.columns(2)
                    for idx, (index, match) in enumerate(row_matches.iterrows()):
                        with cols[idx]:
                            with st.container(border=True):
                                # Layout: LogoCasa | Risultato | LogoTrasferta
                                cL, cC, cR = st.columns([1, 2, 1])
                                hl = trova_logo(match['Casa'])
                                al = trova_logo(match['Trasferta'])
                                
                                with cL:
                                    if hl: st.image(hl, width=40)
                                with cR:
                                    if al: st.image(al, width=40)
                                with cC:
                                    st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:24px; color:#1f77b4'>{match['Risultato']}</div>", unsafe_allow_html=True)
                                
                                # Nomi e Punti Sotto
                                st.markdown(f"""
                                <div style='text-align:center; font-size:14px; margin-top:5px'>
                                    <b>{match['Casa']}</b> vs <b>{match['Trasferta']}</b><br>
                                    <span style='color:#ffbd45; font-size:16px; font-weight:bold;'>({match['Punti_Casa']} - {match['Punti_Trasferta']})</span>
                                </div>
                                """, unsafe_allow_html=True)
                st.markdown("---")

    # --- KPI CUSTOM CARD ---
    def card(label, name, val, sub, icon):
        return f"""
        <div style="background-color:white; padding:10px; border-radius:8px; border:1px solid #ddd; text-align:center; height: 120px; color:black;">
            <div style="font-size:12px; color:#555; margin-bottom:5px;">{icon} {label}</div>
            <div style="font-weight:bold; font-size:16px; margin-bottom:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:black;">{name}</div>
            <div style="font-size:20px; font-weight:bold; color:#1f77b4; margin-bottom:5px;">{val}</div>
            <div style="font-size:11px; color:#333;">{sub}</div>
        </div>
        """

    c1, c2, c3, c4, c5 = st.columns(5)
    
    top = df.loc[df['Gol_Totali'].idxmax()]
    c1.markdown(card("Capocannoniere", top['Giocatore'], f"{int(top['Gol_Totali'])} Gol", top['Fanta_Squadra'], "👑"), unsafe_allow_html=True)
    
    ass = df.loc[df['Assist'].idxmax()]
    c2.markdown(card("Assist Man", ass['Giocatore'], f"{int(ass['Assist'])} Assist", ass['Fanta_Squadra'], "👟"), unsafe_allow_html=True)
    
    portieri = df[(df['Ruolo']=='P') & (df['Partite_Giocate'] > 4)].sort_values('Gol_Subiti')
    best_p = portieri.iloc[0] if not portieri.empty else df.iloc[0]
    c3.markdown(card("Saracinesca", best_p['Giocatore'], f"{int(best_p['Gol_Subiti'])} Subiti", best_p['Fanta_Squadra'], "🧤"), unsafe_allow_html=True)
    
    df['Malus_Tot'] = df['Ammonizioni'] + (df['Espulsioni'] * 3)
    cattivo = df.loc[df['Malus_Tot'].idxmax()]
    c4.markdown(card("Il Cattivo", cattivo['Giocatore'], f"{int(cattivo['Malus_Tot'])} Malus", cattivo['Fanta_Squadra'], "🟨"), unsafe_allow_html=True)

    rigorista = df.loc[df['Rigori_Segnati'].idxmax()]
    c5.markdown(card("Cecchino", rigorista['Giocatore'], f"{int(rigorista['Rigori_Segnati'])} Rig. Segnati", rigorista['Fanta_Squadra'], "🎯"), unsafe_allow_html=True)

    # TABS
    tab_class, tab_squadra, tab_giocatori, tab_match = st.tabs(["🏆 Classifica", "🏢 Scheda Squadra", "🏃 Giocatori", "🆚 Confronto"])

    # --- TAB 1: CLASSIFICA PRO ---
    with tab_class:
        if os.path.exists(FILE_CLASSIFICA):
            df_cl = leggi_excel_intelligente(FILE_CLASSIFICA)
            if df_cl is not None:
                df_cl = df_cl.loc[:, ~df_cl.columns.str.contains('^Unnamed')]
                df_cl = df_cl.dropna(how='all', axis=1)

                stats_squadre = df.groupby('Fanta_Squadra')[['Media_Voto', 'Fanta_Media']].mean().reset_index()
                col_squadra = next((c for c in df_cl.columns if 'squadra' in c.lower()), None)
                
                if col_squadra:
                    df_cl = pd.merge(df_cl, stats_squadre, left_on=col_squadra, right_on='Fanta_Squadra', how='left')
                    
                    headers = st.columns([0.5, 0.5, 3, 1, 1, 1, 1, 1, 1, 1, 1])
                    labels = ["#", "", "Squadra (Click)", "G", "V", "N", "P", "Pt.", "Tot", "MV", "FM"]
                    for c, l in zip(headers, labels):
                        c.markdown(f"**{l}**")
                    st.divider()
                    
                    for idx, row in df_cl.iterrows():
                        cols = st.columns([0.5, 0.5, 3, 1, 1, 1, 1, 1, 1, 1, 1])
                        logo_path = trova_logo(row[col_squadra])
                        
                        cols[0].write(f"**{idx + 1}**")
                        with cols[1]:
                            if logo_path: st.image(logo_path, width=25)
                        
                        # Link Button
                        if cols[2].button(f"**{row[col_squadra]}**", key=f"lnk_{idx}"):
                            st.session_state['selected_team'] = row[col_squadra]
                            st.toast(f"Vai a 'Scheda Squadra' per {row[col_squadra]}")
                        
                        cols[3].write(str(int(row.get('G', 0))))
                        cols[4].write(str(int(row.get('V', 0))))
                        cols[5].write(str(int(row.get('N', 0))))
                        cols[6].write(str(int(row.get('P', 0))))
                        cols[7].markdown(f"<span style='color:#d62728; font-weight:bold'>{row.get('Pt.', 0)}</span>", unsafe_allow_html=True)
                        cols[8].markdown(f"<span style='color:#1f77b4; font-weight:bold'>{row.get('Pt. Totali', 0)}</span>", unsafe_allow_html=True)
                        cols[9].markdown(f"<span style='color:green'>{row.get('Media_Voto', 0):.2f}</span>", unsafe_allow_html=True)
                        cols[10].markdown(f"<span style='color:purple; font-weight:bold'>{row.get('Fanta_Media', 0):.2f}</span>", unsafe_allow_html=True)
                        st.markdown("<hr style='margin: 0px 0; border-top: 1px solid #eee'>", unsafe_allow_html=True)
            else: st.info("Manca File Classifica")

    # --- TAB 2: SCHEDA SQUADRA ---
    with tab_squadra:
        teams = sorted(df['Fanta_Squadra'].unique())
        default_idx = 0
        if 'selected_team' in st.session_state and st.session_state['selected_team'] in teams:
            default_idx = teams.index(st.session_state['selected_team'])
            
        sel_team_profile = st.selectbox("Seleziona Squadra:", teams, index=default_idx)
        
        logo_t = trova_logo(sel_team_profile)
        c1, c2 = st.columns([1, 6])
        with c1: 
            if logo_t: st.image(logo_t, width=100)
        with c2: 
            st.title(sel_team_profile)
        
        if os.path.exists(FILE_CALENDARIO):
            df_cal = parse_calendario_complesso(FILE_CALENDARIO)
            if df_cal is not None:
                future = df_cal[
                    ((df_cal['Casa'] == sel_team_profile) | (df_cal['Trasferta'] == sel_team_profile)) & 
                    (df_cal['Risultato'].isna() | (df_cal['Risultato'] == "") | (df_cal['Risultato'] == "-"))
                ]
                if not future.empty:
                    nm = future.iloc[0]
                    adv = nm['Trasferta'] if nm['Casa'] == sel_team_profile else nm['Casa']
                    st.info(f"📅 Prossimo Turno (G{nm['Giornata_Lega']}): contro **{adv}**")
        
        d_team = df[df['Fanta_Squadra'] == sel_team_profile]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Media Voto Rosa", f"{d_team['Media_Voto'].mean():.2f}")
        m2.metric("FantaMedia Rosa", f"{d_team['Fanta_Media'].mean():.2f}")
        m3.metric("Gol Totali", f"{int(d_team['Gol_Totali'].sum())}")
        m4.metric("Valore Rosa", f"{d_team['Costo'].sum()}")
        
        st.subheader("Rosa")
        d_team = d_team.sort_values('Ruolo', key=lambda x: x.map({'P':0, 'D':1, 'C':2, 'A':3}))
        d_team['Pos'] = range(1, len(d_team)+1)
        
        # ALTEZZA DINAMICA (SHOW ALL)
        h_table = (len(d_team) + 1) * 35 + 3
        st.dataframe(
            d_team[['Pos', 'Ruolo', 'Giocatore', 'Status_Probabile', 'Media_Voto', 'Fanta_Media', 'Gol_Totali', 'Partite_Giocate']].style.map(applica_stile_ruoli, subset=['Ruolo']),
            use_container_width=True, 
            hide_index=True,
            height=h_table,
            column_config=get_table_config()
        )

    # --- TAB 3: GIOCATORI ---
    with tab_giocatori:
        st.subheader("Top Performers")
        c_r, c_o = st.columns(2)
        ruolo = c_r.radio("Filtro Ruolo", ["Tutti", "P", "D", "C", "A"], horizontal=True)
        order = c_o.selectbox("Ordina", ["Fanta_Media", "Gol_Totali", "Assist", "Media_Voto"])
        
        view = df.copy()
        if ruolo != "Tutti": view = view[view['Ruolo'] == ruolo]
        view = view.sort_values(order, ascending=False)
        view['Pos'] = range(1, len(view) + 1)
        
        st.dataframe(
            view.head(50)[['Pos', 'Ruolo', 'Giocatore', 'Status_Probabile', 'Fanta_Squadra', 'Fanta_Media', 'Media_Voto', 'Gol_Totali', 'Assist', 'Partite_Giocate']].style.map(applica_stile_ruoli, subset=['Ruolo']),
            use_container_width=True, hide_index=True,
            column_config=get_table_config()
        )
        
        st.divider()
        st.markdown("##### 📇 Dettaglio Giocatore")
        sel_pl = st.selectbox("Cerca Nome:", sorted(df['Giocatore'].unique()), index=None)
        if sel_pl:
            p = df[df['Giocatore'] == sel_pl].iloc[0]
            col_c = get_role_color(p['Ruolo'])
            img = trova_immagine(p['Giocatore'])
            
            c1, c2 = st.columns([1, 4])
            with c1:
                if img: st.image(img, width=120)
                else: st.markdown(f"<div style='background:{col_c};width:100px;height:100px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:30px;font-weight:bold'>{p['Ruolo']}</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<h3 style='color:{col_c}; margin:0'>{p['Giocatore']} {p['Status_Probabile']}</h3>", unsafe_allow_html=True)
                st.markdown(f"**{p['Fanta_Squadra']}**")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("MV", f"{p['Media_Voto']:.2f}")
                k2.metric("FM", f"{p['Fanta_Media']:.2f}")
                k3.metric("Gol", f"{int(p['Gol_Totali'])}")
                k4.metric("Assist", f"{int(p['Assist'])}")
            
            if os.path.exists(FILE_HISTORY):
                df_h = pd.read_csv(FILE_HISTORY)
                ph = df_h[df_h['clean_name'] == normalizza_nome(p['Giocatore'])].sort_values('Giornata').tail(5)
                if not ph.empty:
                    st.line_chart(ph.set_index('Giornata')['Fantavoto'])

    # --- TAB 4: CONFRONTO ---
    with tab_match:
        c1, c2 = st.columns(2)
        ta = c1.selectbox("Squadra A", sorted(df['Fanta_Squadra'].unique()), index=0)
        tb = c2.selectbox("Squadra B", sorted(df['Fanta_Squadra'].unique()), index=1)
        
        da = df[df['Fanta_Squadra'] == ta]
        db = df[df['Fanta_Squadra'] == tb]
        la, lb = trova_logo(ta), trova_logo(tb)

        def row_confronto(label, val_a, val_b, lower_better=False):
            color_a, color_b = "#333", "#333"
            if val_a != val_b:
                if lower_better:
                    if val_a < val_b: color_a, color_b = "green", "red"
                    else: color_a, color_b = "red", "green"
                else:
                    if val_a > val_b: color_a, color_b = "green", "red"
                    else: color_a, color_b = "red", "green"
            
            return f"""
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #eee; padding:8px 0; color: black;">
                <div style="width:30%; text-align:center; font-weight:bold; font-size:18px; color:{color_a}">{val_a}</div>
                <div style="width:40%; text-align:center; font-size:14px; color:#666;">{label}</div>
                <div style="width:30%; text-align:center; font-weight:bold; font-size:18px; color:{color_b}">{val_b}</div>
            </div>
            """

        col_L, col_C, col_R = st.columns([1, 2, 1])
        with col_L:
            if la: st.image(la, width=80)
            st.markdown(f"<h3 style='text-align:center'>{ta}</h3>", unsafe_allow_html=True)
        with col_R:
            if lb: st.image(lb, width=80)
            st.markdown(f"<h3 style='text-align:center'>{tb}</h3>", unsafe_allow_html=True)
        
        with col_C:
            st.markdown("#### Confronto Statistico")
            mv_a, mv_b = round(da['Media_Voto'].mean(), 2), round(db['Media_Voto'].mean(), 2)
            fm_a, fm_b = round(da['Fanta_Media'].mean(), 2), round(db['Fanta_Media'].mean(), 2)
            gol_a, gol_b = int(da['Gol_Totali'].sum()), int(db['Gol_Totali'].sum())
            ass_a, ass_b = int(da['Assist'].sum()), int(db['Assist'].sum())
            mal_a = int(da['Ammonizioni'].sum() + da['Espulsioni'].sum()*3)
            mal_b = int(db['Ammonizioni'].sum() + db['Espulsioni'].sum()*3)
            val_a, val_b = int(da['Costo'].sum()), int(db['Costo'].sum())

            st.markdown(row_confronto("Media Voto Rosa", mv_a, mv_b), unsafe_allow_html=True)
            st.markdown(row_confronto("FantaMedia Rosa", fm_a, fm_b), unsafe_allow_html=True)
            st.markdown(row_confronto("Gol Totali", gol_a, gol_b), unsafe_allow_html=True)
            st.markdown(row_confronto("Assist Totali", ass_a, ass_b), unsafe_allow_html=True)
            st.markdown(row_confronto("Malus (Disciplina)", mal_a, mal_b, lower_better=True), unsafe_allow_html=True)
            st.markdown(row_confronto("Valore Rosa (Crediti)", val_a, val_b), unsafe_allow_html=True)

elif not df.empty:
    st.info("Caricamento...")
else:
    st.warning("Carica il file Rose.")
