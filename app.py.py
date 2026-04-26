import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Import your engine (make sure pfff_engine.py is in the same folder)
from pfff_engine import PROJECTS, compute_scn, run_mcs, simulate_mode, spearman_tornado, MODES, HURDLES, fi_color, verdict

# ─── PAGE CONFIGURATION & CSS ───────────────────────────────────────────
st.set_page_config(page_title="PFFF | NHAI Audit", layout="wide", initial_sidebar_state="expanded")

# Injecting NHAI-style Corporate CSS
st.markdown("""
    <style>
    .main {background-color: #F8F9FA;}
    h1, h2, h3 {color: #1F497D;}
    .metric-card {
        background-color: white; border-radius: 8px; padding: 20px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #1F497D;
    }
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; font-size: 16px;}
    </style>
""", unsafe_allow_html=True)

st.title("🏛️ PFFF v11.0: Decision Support System")
st.markdown("**Probabilistic Feasibility Fragility Framework** | SPA Delhi MIS Portal")

# ─── SIDEBAR: INTERACTIVE INPUTS ────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Project Parameters")
    
    # 1. Select Project
    project_code = st.selectbox("Select DPR to Audit:", list(PROJECTS.keys()), 
                                format_func=lambda x: PROJECTS[x]["name"])
    p_data = PROJECTS[project_code].copy()
    
    st.markdown("---")
    st.subheader("What-If Override (Stress Test)")
    
    # 2. Interactive Sliders (Overrides DPR defaults)
    p_data["la_pct"] = st.slider("Land Acquisition (LA %)", 0, 100, p_data["la_pct"], 5)
    
    p_data["geotech"] = st.select_slider("Geotech Quality", 
                                         options=["DESKTOP", "PARTIAL", "COMPLETE"], 
                                         value=p_data["geotech"])
    
    p_data["contractor"] = st.select_slider("Contractor Capability", 
                                            options=["STRESSED", "ADEQUATE", "STRONG"], 
                                            value=p_data["contractor"])
    
    # Run Button
    run_audit = st.button("🚀 Perform Forensic Audit", type="primary", use_container_width=True)

# ─── EXECUTION ENGINE (CACHED FOR SPEED) ───────────────────────────────
@st.cache_data
def run_simulation(p):
    scn = compute_scn(p)
    samp = run_mcs(p, scn)
    results = {mode: simulate_mode(p, scn, samp, mode) for mode in MODES}
    tornado = spearman_tornado(p, scn, samp, results[p["dpr_mode"]]["eirr_arr"])
    return scn, samp, results, tornado

# Default run on load or button click
scn, samp, results, tornado = run_simulation(p_data)
dpr_mode = p_data["dpr_mode"]
main_res = results[dpr_mode]
fi_val = main_res["fi_p"]

# ─── TOP LEVEL METRICS (MIS STYLE) ─────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <p style="margin:0; color:#6C757D; font-size:14px;">Fragility Index (FI)</p>
        <h2 style="margin:0; color:{fi_color(fi_val)[1]}; font-size:36px;">{fi_val:.1f}%</h2>
        <p style="margin:0; color:#1F497D; font-weight:bold;">{verdict(fi_val).split('—')[0]}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.metric(label="DPR Stated EIRR", value=f"{p_data['dpr_eirr']:.2f}%", 
              delta=f"Hurdle: {HURDLES['EIRR']*100}%", delta_color="off")
with col3:
    st.metric(label="Simulated Median (P50)", value=f"{np.percentile(main_res['eirr_arr']*100, 50):.2f}%")
with col4:
    st.metric(label="Primary Risk Driver", value=f"{tornado[0][0]}")

st.markdown("<br>", unsafe_allow_html=True)

# ─── INTERACTIVE TABS ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Forensic Analytics (Plotly)", "🛡️ Procurement Pivot", "📋 Data Audit"])

with tab1:
    st.subheader("Interactive Distribution Analytics")
    colA, colB = st.columns([3, 2])
    
    with colA:
        # PLOTLY CHART 1: Interactive Bell Curve (Hoverable)
        eirr_pct = main_res["eirr_arr"] * 100
        fig1 = go.Figure()
        fig1.add_trace(go.Histogram(x=eirr_pct, nbinsx=60, marker_color='#0D6EFD', opacity=0.75, 
                                    name="Simulated Outcomes", hovertemplate="EIRR: %{x:.1f}%<br>Count: %{y}"))
        
        # Vertical Lines
        fig1.add_vline(x=12.0, line_dash="dash", line_color="red", line_width=2, annotation_text="12% Hurdle")
        fig1.add_vline(x=p_data["dpr_eirr"], line_color="black", line_width=2, annotation_text="DPR Stated")
        
        fig1.update_layout(title="Economic Viability (EIRR) Stress Test", 
                           xaxis_title="EIRR (%)", yaxis_title="Frequency", 
                           hovermode="x unified", plot_bgcolor="white")
        st.plotly_chart(fig1, use_container_width=True)

    with colB:
        # PLOTLY CHART 2: Interactive Spearman Tornado
        names = [t[0] for t in tornado[:6]][::-1]
        rhos = [t[1] for t in tornado[:6]][::-1]
        colors = ['#DC3545' if r < 0 else '#0D6EFD' for r in rhos]
        
        fig2 = go.Figure(go.Bar(
            x=rhos, y=names, orientation='h', marker_color=colors,
            hovertemplate="Impact Factor: %{x:.3f}<extra></extra>"
        ))
        fig2.add_vline(x=0, line_color="black", line_width=1)
        fig2.update_layout(title="What is driving the Fragility?", 
                           xaxis_title="Spearman Correlation", plot_bgcolor="white")
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader("Procurement Mode Optimization")
    st.markdown("Instantly compare the financial survival of this project across different NHAI delivery modes.")
    
    # PLOTLY CHART 3: Bar chart for Procurement Modes
    modes = MODES
    fi_scores = [results[m]["fi_p"] for m in modes]
    bar_colors = [fi_color(f)[1] for f in fi_scores]
    
    fig3 = go.Figure(go.Bar(
        x=modes, y=fi_scores, marker_color=bar_colors, text=[f"{f:.1f}%" for f in fi_scores], textposition='auto'
    ))
    fig3.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="RED Threshold")
    fig3.add_hline(y=25, line_dash="dash", line_color="orange", annotation_text="AMBER Threshold")
    
    fig3.update_layout(yaxis_title="Fragility Index (%)", yaxis_range=[0, 105], plot_bgcolor="white")
    st.plotly_chart(fig3, use_container_width=True)
    
    # Insight Logic
    best_mode = modes[np.argmin(fi_scores)]
    worst_mode = modes[np.argmax(fi_scores)]
    if fi_scores[np.argmax(fi_scores)] - fi_scores[np.argmin(fi_scores)] > 20:
        st.success(f"**Strategic Insight:** Procurement Mismatch detected. Pivoting to **{best_mode}** reduces fragility significantly compared to **{worst_mode}**.")

with tab3:
    st.subheader("SCN Diagnostics")
    st.json(scn)  # Displays the SCN logic transparently