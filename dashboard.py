import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# --- 1. OPSÆTNING & DATABASE ---
st.set_page_config(page_title="Himmelstrup SEO", layout="wide", page_icon="🚀")

@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection()

# --- 2. HENT DATA FUNKTIONER ---
def get_seo_data():
    """Henter snapshots til grafer og KPI'er"""
    response = supabase.table("seo_snapshots").select("*").order("created_at", desc=True).limit(30).execute()
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at'])
    return df

def get_pending_tasks():
    """Henter kun opgaver der IKKE er løst endnu"""
    response = supabase.table("seo_tasks")\
        .select("*")\
        .eq("status", "pending")\
        .order("created_at", desc=True)\
        .execute()
    return response.data

def mark_task_done(task_id):
    """Opdaterer status til 'done' i databasen"""
    supabase.table("seo_tasks").update({"status": "done"}).eq("id", task_id).execute()
    st.cache_data.clear() # Ryd cache så listen opdateres med det samme
    st.rerun()

# --- 3. DASHBOARD UI ---
st.title("🚀 Himmelstrup Events SEO Status")

# Hent data
df = get_seo_data()
tasks = get_pending_tasks()

if df.empty:
    st.warning("Venter på første datakørsel...")
else:
    # --- KPI SEKTION ---
    latest = df.iloc[0]
    
    # Beregn ændringer sikkert (håndter NaN/Null)
    delta_score = 0
    delta_clicks = 0
    
    if len(df) > 1:
        previous = df.iloc[1]
        
        score_now = 0 if pd.isna(latest['overall_score']) else int(latest['overall_score'])
        score_prev = 0 if pd.isna(previous['overall_score']) else int(previous['overall_score'])
        delta_score = score_now - score_prev
        
        clicks_now = 0 if pd.isna(latest['gsc_clicks']) else int(latest['gsc_clicks'])
        clicks_prev = 0 if pd.isna(previous['gsc_clicks']) else int(previous['gsc_clicks'])
        delta_clicks = clicks_now - clicks_prev

    # Vis KPI'er
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall SEO Score", f"{latest['overall_score']}/100", delta_score)
    with col2:
        st.metric("Organisk Trafik (30 dage)", f"{latest['gsc_clicks']} klik", delta_clicks)
    with col3:
        st.metric("PageSpeed (Mobil)", f"{latest['psi_mobile_score']}/100", help="Mål: >90")
    with col4:
        lcp_val = latest['psi_lcp']
        st.metric("LCP (Load Tid)", f"{lcp_val} s", delta_color="inverse" if lcp_val > 2.5 else "normal", help="Mål: <2.5s")

    st.divider()

    # --- OPGAVE SEKTION (NY!) ---
    st.header(f"📋 Handlingsplan ({len(tasks)} opgaver)")
    
    if not tasks:
        st.success("🎉 Ingen åbne opgaver! Godt arbejde.")
    else:
        # Vis opgaverne i et grid
        for task in tasks:
            # Bestem farve baseret på prioritet
            priority_color = "🔴" if task['priority'] == "Høj" else "🟡" if task['priority'] == "Medium" else "🔵"
            
            with st.expander(f"{priority_color} {task['task_name']} ({task['task_type']})", expanded=True):
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    st.markdown(f"**Hvorfor?**\n{task['description_why']}")
                    st.info(f"💡 **Løsning:** {task['description_how']}")
                
                with c2:
                    st.write("") # Spacer
                    st.write("") 
                    if st.button("✅ Marker som løst", key=task['id'], use_container_width=True):
                        mark_task_done(task['id'])

    st.divider()

    # --- GRAF SEKTION ---
    col_ai, col_graph = st.columns([1, 2])

    with col_ai:
        st.subheader("🤖 Sidste AI Analyse")
        if latest['semantisk_analyse']:
            st.info(latest['semantisk_analyse'])
        else:
            st.text("Ingen analyse tekst fundet.")
        st.caption(f"Opdateret: {latest['created_at'].strftime('%d-%m-%Y %H:%M')}")

    with col_graph:
        st.subheader("📈 Udvikling")
        tab1, tab2 = st.tabs(["Trafik", "Teknik"])
        
        with tab1:
            fig_traffic = px.line(df, x="created_at", y=["gsc_clicks", "gsc_impressions"], markers=True)
            st.plotly_chart(fig_traffic, use_container_width=True)
            
        with tab2:
            fig_tech = px.line(df, x="created_at", y=["psi_mobile_score", "overall_score"], markers=True)
            st.plotly_chart(fig_tech, use_container_width=True)