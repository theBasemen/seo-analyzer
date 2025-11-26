import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. OPSÆTNING ---
st.set_page_config(page_title="Himmelstrup SEO", layout="wide", page_icon="bar_chart")

# Custom CSS for et rent, professionelt sort/hvidt look
st.markdown("""
<style>
    .streamlit-expanderHeader {font-size: 16px; font-weight: 600; color: #333;}
    div[data-testid="stMetricValue"] {font-size: 28px; font-family: 'Helvetica', sans-serif;}
    h1, h2, h3 {color: #000 !important;}
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
       font-size: 16px;
       font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Database fejl: {e}")
        st.stop()

supabase = init_connection()

# --- 2. DATA FUNKTIONER ---
def get_seo_data():
    try:
        response = supabase.table("seo_snapshots").select("*").order("created_at", desc=True).limit(30).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
        return df
    except Exception:
        return pd.DataFrame()

def get_pending_tasks():
    try:
        response = supabase.table("seo_tasks").select("*").eq("status", "pending").order("created_at", desc=True).execute()
        return response.data
    except Exception:
        return []

def mark_task_done(task_id):
    supabase.table("seo_tasks").update({"status": "done"}).eq("id", task_id).execute()
    st.cache_data.clear()
    st.rerun()

# Hjælpefunktion til stilrene grafer
def clean_plot(fig):
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_color="black",
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="x unified"
    )
    fig.update_xaxes(showgrid=False, linecolor='black')
    fig.update_yaxes(showgrid=True, gridcolor='#eeeeee', linecolor='black')
    return fig

# --- 3. DASHBOARD START ---
st.title("Himmelstrup Events SEO")
st.markdown("---")

df = get_seo_data()
tasks = get_pending_tasks()

if df.empty:
    st.info("Systemet indsamler data...")
    st.stop()

# --- TOP KPI SEKTION ---
latest = df.iloc[0]
delta_score = 0 
if len(df) > 1:
    delta_score = int(latest['overall_score'] or 0) - int(df.iloc[1]['overall_score'] or 0)

# KPI Grid
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Overall Score", f"{latest['overall_score']}/100", delta_score)
with col2:
    st.metric("Trafik (30d)", f"{latest['gsc_clicks']}", help="Organiske klik")
with col3:
    st.metric("PageSpeed", f"{latest['psi_mobile_score']}/100")
with col4:
    lcp_val = latest['psi_lcp']
    # Bruger standard delta colors da de er universelle (grøn/rød) for metrics
    st.metric("LCP Tid", f"{lcp_val} s", delta_color="inverse" if lcp_val > 2.5 else "normal")

st.write("") 

# --- HOVED FANER ---
# Fjernet emojis, bruger rene titler
tab_overview, tab_tasks, tab_products = st.tabs(["Analyse & Grafer", f"Handlingsplan ({len(tasks)})", "Produkter"])

# --- FANE 1: GRAFER & ANALYSE ---
with tab_overview:
    # AI Analyse - Rent tekst format
    st.subheader("Status & Analyse")
    if latest.get('semantisk_analyse'):
        st.info(latest['semantisk_analyse'], icon="ℹ️") # Standard info icon er diskret
    else:
        st.text("Ingen analyse tekst fundet.")
    st.caption(f"Sidst opdateret: {latest['created_at'].strftime('%d-%m %H:%M')}")
    
    st.divider()
    
    # Grafer - Sort/Hvid tema
    st.subheader("Detaljeret Udvikling")
    
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        # GRAF 1: TEKNISK SCORE
        fig_score = px.line(df, x="created_at", y="psi_mobile_score", 
                          title="Mobil Score",
                          markers=True,
                          color_discrete_sequence=["black"]) # Sort linje
        fig_score.add_hline(y=90, line_dash="dot", annotation_text="Mål", annotation_position="bottom right", line_color="#999")
        fig_score.update_yaxes(range=[0, 105])
        st.plotly_chart(clean_plot(fig_score), use_container_width=True)

        # GRAF 3: KLIK
        fig_clicks = px.line(df, x="created_at", y="gsc_clicks", 
                           title="Organiske Klik",
                           markers=True,
                           color_discrete_sequence=["black"])
        # Tilføj fill under grafen for visuel vægt
        fig_clicks.update_traces(fill='tozeroy', fillcolor='rgba(0,0,0,0.05)') 
        st.plotly_chart(clean_plot(fig_clicks), use_container_width=True)

    with g_col2:
        # GRAF 2: LCP
        fig_lcp = px.line(df, x="created_at", y="psi_lcp", 
                        title="LCP Hastighed (sek)",
                        markers=True,
                        color_discrete_sequence=["black"])
        fig_lcp.add_hline(y=2.5, line_dash="dot", annotation_text="Grænse", annotation_position="top right", line_color="#999")
        st.plotly_chart(clean_plot(fig_lcp), use_container_width=True)

        # GRAF 4: CTR
        fig_ctr = px.line(df, x="created_at", y="gsc_ctr", 
                        title="Click-Through Rate (%)",
                        markers=True,
                        color_discrete_sequence=["black"])
        fig_ctr.add_hline(y=0.02, line_dash="dot", annotation_text="Mål", line_color="#999")
        st.plotly_chart(clean_plot(fig_ctr), use_container_width=True)

# --- FANE 2: OPGAVER ---
with tab_tasks:
    st.write("")
    if not tasks:
        st.success("Ingen åbne opgaver.")
    else:
        st.markdown("##### Aktuelle indsatser")
        for task in tasks:
            # Minimalistiske ikoner
            prio_icon = "⚡" if task.get('priority') == "Høj" else "○"
            
            with st.expander(f"{prio_icon} {task['task_name']}  |  {task.get('task_type', 'Opgave')}"):
                c_desc, c_btn = st.columns([4, 1])
                with c_desc:
                    if task.get('description_why'):
                        st.markdown(f"**Hvorfor:** {task['description_why']}")
                    if task.get('description_how'):
                        st.markdown(f"**Løsning:** {task['description_how']}")
                with c_btn:
                    st.write("") 
                    if st.button("Marker som udført", key=f"btn_{task['id']}", use_container_width=True):
                        mark_task_done(task['id'])

# --- FANE 3: PRODUKTER ---
with tab_products:
    st.subheader("Produkt Performance")

    try:
        vip_data = supabase.table("page_performance")\
            .select("*")\
            .order("created_at", desc=True)\
            .limit(1000)\
            .execute()
            
        if vip_data.data:
            df_vip = pd.DataFrame(vip_data.data)
            df_vip['created_at'] = pd.to_datetime(df_vip['created_at'])
            
            latest_date = df_vip['created_at'].max()
            df_latest = df_vip[df_vip['created_at'] == latest_date].sort_values('clicks', ascending=False)

            # Tabel med rene progress bars
            st.dataframe(
                df_latest[['page_name', 'clicks', 'impressions', 'ctr', 'position']],
                column_config={
                    "page_name": "Side",
                    "clicks": st.column_config.NumberColumn("Klik", format="%d"),
                    "impressions": st.column_config.NumberColumn("Visninger", format="%d"),
                    "ctr": st.column_config.ProgressColumn("CTR", format="%.2f%%", min_value=0, max_value=0.05),
                    "position": st.column_config.NumberColumn("Ranking", format="%.1f"),
                },
                hide_index=True,
                use_container_width=True
            )

            st.divider()
            st.subheader("Dybdegående Analyse")
            
            page_names = df_vip['page_name'].unique()
            selected_page = st.selectbox("Vælg side:", page_names, index=0)
            
            page_history = df_vip[df_vip['page_name'] == selected_page].sort_values("created_at")

            if not page_history.empty:
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    fig_rank = px.line(page_history, x="created_at", y="position", 
                                     title=f"Ranking: {selected_page}",
                                     markers=True,
                                     color_discrete_sequence=["black"])
                    fig_rank['layout']['yaxis']['autorange'] = "reversed" 
                    st.plotly_chart(clean_plot(fig_rank), use_container_width=True)
                    
                with col_g2:
                    fig_traf = px.line(page_history, x="created_at", y=["impressions", "clicks"], 
                                     title=f"Trafik: {selected_page}",
                                     markers=True,
                                     color_discrete_map={"impressions": "#999999", "clicks": "#000000"}) # Grå for visninger, sort for klik
                    st.plotly_chart(clean_plot(fig_traf), use_container_width=True)
                    
                fig_ctr = px.line(page_history, x="created_at", y="ctr", 
                                title="CTR (%)",
                                markers=True,
                                color_discrete_sequence=["black"])
                st.plotly_chart(clean_plot(fig_ctr), use_container_width=True)
        else:
            st.info("Ingen data fundet endnu.")
            
    except Exception as e:
        st.error(f"Kunne ikke hente produkt-data: {e}")