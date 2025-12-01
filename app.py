import streamlit as st
import pandas as pd
import os
import glob
import re
import sys

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

# --- CSS PERSONALIZZATO (PER KPI E COLORI) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #1f77b4;
    }
    [data-testid="stMetricLabel"] {
        font-size: 16px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. FUNZIONI DI UTILITÀ ---

def normalizza_nome(nome):
    if pd.isna(nome): return ""
    return str(nome).lower().strip().replace(".", "").replace("'", "")

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
    # Match esatto
    for f in files:
        if normalizza_nome(f.split('.')[0]) == nome_clean: 
            return os.path.join(DIR_LOGO, f)
    # Match parziale
    for f in files:
        if nome_clean in normalizza_nome(f.split('.')[0]): 
            return os.path.join(DIR_LOGO, f)
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
                        g_lega_match = re.search(r'(\d+)', cell_val)
                        if not g_lega_match: continue
                        g_lega = int(g_lega_match.group(1))
                        
                        g_seriea = "?"
                        if c+2 < cols:
                            serie_a_str = str(df.iat[r, c+2]).lower()
                            if "serie a" in serie_a_str:
                                found = re.search(r'(\d+)', serie_a_str)
                                if found: g_seriea = found.group(1)
                        
                        curr = r + 1
                        while curr < rows:
                            home = df.iat[curr, c]
                            if pd.isna(home) or "giornata" in str(home).lower(): break
                            
                            pt_h = df.iat[curr, c+1] # Punti Casa
                            pt_a = df.iat[curr, c+2] # Punti Trasferta
                            away = df.iat[curr, c+3]
                            res = df.iat[curr, c+4]
                            
                            matches.append({
                                'Giornata_Lega': g_lega, 
                                'Giornata_SerieA': g_seriea,
                                'Casa': home, 'Punti_Casa': pt_h,
                                'Punti_Trasferta': pt_a, 'Trasferta': away, 
                                'Risultato': res
                            })
                            curr += 1
                    except Exception: continue
        
        if matches:
            return pd.DataFrame(matches).sort_values('Giornata_Lega')
        return None
    except Exception: return None

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
                            'Rigori_Parati': 0, 'Autoreti': 0
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
                if col_name:
                    return pd.to_numeric(df_in[col_name], errors='coerce').fillna(0)
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

    if history_records:
        pd.concat(history_records).to_csv(FILE_HISTORY, index=False)

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

if not df.empty and df['Partite_Giocate'].sum() > 0:

    # --- 1. ULTIMA GIORNATA (LAYOUT "STADIO" con PUNTI) ---
    if os.path.exists(FILE_CALENDARIO):
        df_cal = parse_calendario_complesso(FILE_CALENDARIO)
        if df_cal is not None:
            giocate = df_cal[df_cal['Risultato'].astype(str).str.contains(r'\d', na=False)]
            
            if not giocate.empty:
                last_g = giocate['Giornata_Lega'].max()
                matches_last = giocate[giocate['Giornata_Lega'] == last_g]
                
                with st.container():
                    st.markdown(f"### 🏟️ Ultimo Turno: Giornata {last_g}")
                    cols = st.columns(4) 
                    for idx, (_, row) in enumerate(matches_last.iterrows()):
                        col_target = cols[idx % 4]
                        with col_target:
                            hl = trova_logo(row['Casa'])
                            al = trova_logo(row['Trasferta'])
                            
                            with st.container(border=True):
                                # Intestazione con Loghi
                                c_h, c_res, c_a = st.columns([1, 2, 1])
                                with c_h:
                                    if hl: st.image(hl, width=40)
                                    st.caption(row['Casa'])
                                with c_res:
                                    # Risultato Grande
                                    st.markdown(f"<h2 style='text-align: center; margin:0; color:#1f77b4'>{row['Risultato']}</h2>", unsafe_allow_html=True)
                                    # Punti Piccolo
                                    st.markdown(f"<div style='text-align: center; font-size:12px; color:gray'>{row['Punti_Casa']} - {row['Punti_Trasferta']}</div>", unsafe_allow_html=True)
                                with c_a:
                                    if al: st.image(al, width=40)
                                    st.caption(row['Trasferta'])
                    st.markdown("---")

    # KPI (RE-DESIGN: NOME sopra, VALORE sotto)
    k1, k2, k3, k4, k5 = st.columns(5)
    
    top = df.loc[df['Gol_Totali'].idxmax()]
    k1.metric(f"👑 Capocannoniere: {top['Giocatore']}", f"{int(top['Gol_Totali'])} Gol", top['Fanta_Squadra'], delta_color="off")
    
    ass = df.loc[df['Assist'].idxmax()]
    k2.metric(f"👟 Assist Man: {ass['Giocatore']}", f"{int(ass['Assist'])} Assist", ass['Fanta_Squadra'], delta_color="off")
    
    portieri = df[(df['Ruolo']=='P') & (df['Partite_Giocate'] > 4)].sort_values('Gol_Subiti')
    if not portieri.empty:
        best_p = portieri.iloc[0]
        k3.metric(f"🧤 Saracinesca: {best_p['Giocatore']}", f"{int(best_p['Gol_Subiti'])} Subiti", best_p['Fanta_Squadra'], delta_color="off")
    
    df['Malus_Tot'] = df['Ammonizioni'] + (df['Espulsioni'] * 3)
    cattivo = df.loc[df['Malus_Tot'].idxmax()]
    k4.metric(f"🟨 Il Cattivo: {cattivo['Giocatore']}", f"{int(cattivo['Malus_Tot'])} Malus", cattivo['Fanta_Squadra'], delta_color="inverse")

    rigorista = df.loc[df['Rigori_Segnati'].idxmax()]
    k5.metric(f"🎯 Cecchino: {rigorista['Giocatore']}", f"{int(rigorista['Rigori_Segnati'])} Segnati", rigorista['Fanta_Squadra'])

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
                    
                    # HEADER MANUALE
                    cols_head = st.columns([0.5, 0.5, 3, 1, 1, 1, 1, 1, 1, 1, 1])
                    labels = ["#", "", "Squadra", "G", "V", "N", "P", "Pt.", "Tot.Pt", "MV", "FM"]
                    for c, l in zip(cols_head, labels):
                        c.markdown(f"**{l}**")
                    st.divider()
                    
                    for idx, row in df_cl.iterrows():
                        cols = st.columns([0.5, 0.5, 3, 1, 1, 1, 1, 1, 1, 1, 1])
                        logo_path = trova_logo(row[col_squadra])
                        
                        cols[0].write(f"**{idx + 1}**") # Posizione
                        with cols[1]:
                            if logo_path: st.image(logo_path, width=25)
                        cols[2].write(f"**{row[col_squadra]}**")
                        cols[3].write(str(int(row.get('G', 0))))
                        cols[4].write(str(int(row.get('V', 0))))
                        cols[5].write(str(int(row.get('N', 0))))
                        cols[6].write(str(int(row.get('P', 0))))
                        
                        # Punti (Evidenziati)
                        cols[7].markdown(f"<span style='color:#d62728; font-weight:bold'>{row.get('Pt.', 0)}</span>", unsafe_allow_html=True)
                        # Totale Punti (Evidenziati)
                        cols[8].markdown(f"<span style='color:#1f77b4; font-weight:bold'>{row.get('Pt. Totali', 0)}</span>", unsafe_allow_html=True)
                        
                        cols[9].write(f"{row.get('Media_Voto', 0):.2f}")
                        cols[10].write(f"{row.get('Fanta_Media', 0):.2f}")
                        st.markdown("<hr style='margin: 0px 0; border-top: 1px solid #eee'>", unsafe_allow_html=True)
            else: st.info("Manca File Classifica")

    # --- TAB 2: SCHEDA SQUADRA (NUOVA!) ---
    with tab_squadra:
        teams = sorted(df['Fanta_Squadra'].unique())
        sel_team_profile = st.selectbox("Seleziona Squadra per Dettagli:", teams)
        
        logo_t = trova_logo(sel_team_profile)
        col_t1, col_t2 = st.columns([1, 5])
        with col_t1:
            if logo_t: st.image(logo_t, width=100)
        with col_t2:
            st.title(sel_team_profile)
        
        # PROSSIMA PARTITA (Logica Semplice)
        if os.path.exists(FILE_CALENDARIO):
            df_cal = parse_calendario_complesso(FILE_CALENDARIO)
            if df_cal is not None:
                # Trova la prima partita senza risultato per questa squadra
                future = df_cal[
                    ((df_cal['Casa'] == sel_team_profile) | (df_cal['Trasferta'] == sel_team_profile)) & 
                    (df_cal['Risultato'].isna() | (df_cal['Risultato'] == "") | (df_cal['Risultato'] == "-"))
                ]
                if not future.empty:
                    next_match = future.iloc[0]
                    avversario = next_match['Trasferta'] if next_match['Casa'] == sel_team_profile else next_match['Casa']
                    st.info(f"📅 Prossimo Turno (G{next_match['Giornata_Lega']}): contro **{avversario}**")
        
        # STATS SQUADRA
        d_team = df[df['Fanta_Squadra'] == sel_team_profile]
        
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("Media Voto Rosa", f"{d_team['Media_Voto'].mean():.2f}")
        col_s2.metric("FantaMedia Rosa", f"{d_team['Fanta_Media'].mean():.2f}")
        col_s3.metric("Gol Totali", f"{int(d_team['Gol_Totali'].sum())}")
        col_s4.metric("Valore Rosa (Cr)", f"{d_team['Costo'].sum()}")
        
        st.subheader("Rosa Giocatori")
        # Ordina per ruolo (P, D, C, A)
        d_team = d_team.sort_values('Ruolo', key=lambda x: x.map({'P':0, 'D':1, 'C':2, 'A':3}))
        d_team['Pos'] = range(1, len(d_team)+1)
        
        st.dataframe(
            d_team[['Pos', 'Ruolo', 'Giocatore', 'Media_Voto', 'Fanta_Media', 'Gol_Totali', 'Partite_Giocate']].style.map(applica_stile_ruoli, subset=['Ruolo']),
            use_container_width=True, hide_index=True,
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
        
        cols = ['Pos', 'Ruolo', 'Giocatore', 'Fanta_Squadra', 'Fanta_Media', 'Media_Voto', 'Gol_Totali', 'Assist', 'Partite_Giocate']
        
        st.dataframe(
            view.head(50)[cols].style.map(applica_stile_ruoli, subset=['Ruolo']),
            use_container_width=True, hide_index=True,
            column_config=get_table_config()
        )
        
        # Scheda Giocatore in fondo
        st.divider()
        st.markdown("##### 📇 Dettaglio Giocatore")
        sel_pl = st.selectbox("Cerca Nome:", sorted(df['Giocatore'].unique()), index=None)
        if sel_pl:
            p = df[df['Giocatore'] == sel_pl].iloc[0]
            col_c = get_role_color(p['Ruolo'])
            img = trova_immagine(p['Giocatore'])
            
            c_img, c_dati = st.columns([1, 4])
            with c_img:
                if img: st.image(img, width=120)
                else: st.markdown(f"<div style='background:{col_c};width:100px;height:100px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:white;font-size:30px;font-weight:bold'>{p['Ruolo']}</div>", unsafe_allow_html=True)
            with c_dati:
                st.markdown(f"<h3 style='color:{col_c}; margin:0'>{p['Giocatore']}</h3>", unsafe_allow_html=True)
                st.markdown(f"**{p['Fanta_Squadra']}** ({p['Squadra_SerieA']})")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Media Voto", f"{p['Media_Voto']:.2f}")
                m2.metric("FantaMedia", f"{p['Fanta_Media']:.2f}")
                m3.metric("Gol", f"{int(p['Gol_Totali'])}")
                m4.metric("Assist", f"{int(p['Assist'])}")
            
            if os.path.exists(FILE_HISTORY):
                df_h = pd.read_csv(FILE_HISTORY)
                ph = df_h[df_h['clean_name'] == normalizza_nome(p['Giocatore'])].sort_values('Giornata').tail(5)
                if not ph.empty:
                    st.caption("Ultimi 5 Voti:")
                    st.line_chart(ph.set_index('Giornata')['Fantavoto'])

    # --- TAB 4: CONFRONTO ---
    with tab_match:
        teams = sorted(df['Fanta_Squadra'].unique())
        c1, c2 = st.columns(2)
        ta = c1.selectbox("Squadra A", teams, index=0)
        tb = c2.selectbox("Squadra B", teams, index=1)
        
        da = df[df['Fanta_Squadra'] == ta]
        db = df[df['Fanta_Squadra'] == tb]
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Media Voto", f"{da['Fanta_Media'].mean():.2f} vs {db['Fanta_Media'].mean():.2f}")
        k2.metric("Gol Totali", f"{int(da['Gol_Totali'].sum())} vs {int(db['Gol_Totali'].sum())}")
        k3.metric("Valore Rosa", f"{da['Costo'].sum()} vs {db['Costo'].sum()}")

elif not df.empty:
    st.info("Caricamento...")
else:
    st.warning("Carica il file Rose.")