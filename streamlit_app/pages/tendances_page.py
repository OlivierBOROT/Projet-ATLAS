"""
Page d'analyse des tendances du marché
========================================
Affiche les métiers et compétences en tendance avec évolutions temporelles
"""

import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Tendances - ATLAS", page_icon="📈", layout="wide")

# CSS personnalisé
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 class="main-header">📈 Tendances du Marché</h1>', unsafe_allow_html=True
)
st.markdown("**Analyse des métiers et compétences en tendance**")

st.markdown("---")

# ============================================================================
# VÉRIFICATION API
# ============================================================================

try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    if response.status_code != 200:
        st.error("❌ API non accessible")
        st.stop()
except:
    st.error(f"❌ Impossible de se connecter à l'API ({API_URL})")
    st.info("💡 Vérifiez que l'API est lancée")
    st.stop()

# ============================================================================
# SIDEBAR - PARAMÈTRES
# ============================================================================

with st.sidebar:
    st.header("⚙️ Paramètres")

    period_days = st.selectbox(
        "Période d'analyse",
        options=[7, 14, 30, 60, 90, 180],
        index=2,
        format_func=lambda x: f"{x} jours",
    )

    st.markdown("---")
    st.caption(f"Analyse sur les {period_days} derniers jours")

# ============================================================================
# FONCTIONS DE CHARGEMENT
# ============================================================================


@st.cache_data(ttl=600)
def load_profile_trends(days=30):
    """Charge les tendances des métiers"""
    try:
        response = requests.get(
            f"{API_URL}/api/trends/profiles",
            params={"days": days, "limit": 10},
            timeout=10,
        )
        return response.json()
    except Exception as e:
        st.error(f"Erreur: {str(e)}")
        return {"trends": {}, "days": days}


@st.cache_data(ttl=600)
def load_skill_trends(days=30):
    """Charge les tendances des compétences (tech et soft)"""
    try:
        response = requests.get(
            f"{API_URL}/api/trends/skills",
            params={"days": days, "limit": 20},
            timeout=10,
        )
        return response.json()
    except Exception as e:
        st.error(f"Erreur: {str(e)}")
        return {
            "tech_skills": [],
            "tech_timeline": {},
            "soft_skills": [],
            "soft_timeline": {},
            "days": days,
        }


# ============================================================================
# SECTION 1: MÉTIERS EN TENDANCE
# ============================================================================

st.header("👔 Métiers en tendance")

with st.spinner("Chargement des données..."):
    profile_data = load_profile_trends(period_days)
    trends = profile_data.get("trends", {})

if trends:
    # Créer un DataFrame pour Plotly
    data_for_plot = []
    for profile, timeline in trends.items():
        for entry in timeline:
            data_for_plot.append(
                {"date": entry["date"], "profile": profile, "count": entry["count"]}
            )

    df_profiles = pd.DataFrame(data_for_plot)
    df_profiles["date"] = pd.to_datetime(df_profiles["date"])

    # Graphique ligne évolution
    fig_profiles = px.line(
        df_profiles,
        x="date",
        y="count",
        color="profile",
        title=f"Évolution des {len(trends)} métiers les plus demandés ({period_days} derniers jours)",
        labels={"date": "Date", "count": "Nombre d'offres", "profile": "Métier"},
        markers=True,
    )

    fig_profiles.update_layout(
        height=500,
        hovermode="x unified",
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
    )

    st.plotly_chart(fig_profiles, use_container_width=True)

    # Stats agrégées
    st.subheader("📊 Classement des métiers")

    totals = df_profiles.groupby("profile")["count"].sum().sort_values(ascending=False)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig_bar = px.bar(
            x=totals.values,
            y=totals.index,
            orientation="h",
            title="Total d'offres par métier",
            labels={"x": "Nombre d'offres", "y": "Métier"},
            color=totals.values,
            color_continuous_scale="Viridis",
        )
        fig_bar.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown("**🏆 Top 5 métiers**")
        for i, (profile, count) in enumerate(totals.head(5).items(), 1):
            st.markdown(f"{i}. **{profile}**")
            st.markdown(f"   {int(count)} offres")
            st.markdown("")
else:
    st.info("Aucune donnée disponible pour les métiers")

st.markdown("---")

# ============================================================================
# SECTION 2: COMPÉTENCES TECHNIQUES EN TENDANCE
# ============================================================================

st.header("💻 Compétences techniques en tendance")

with st.spinner("Chargement des compétences techniques..."):
    skill_data = load_skill_trends(period_days)
    tech_skills = skill_data.get("tech_skills", [])
    tech_timeline = skill_data.get("tech_timeline", {})

if tech_skills:
    col1, col2 = st.columns([2, 1])

    with col1:
        # Top 20 compétences tech
        df_tech = pd.DataFrame(tech_skills)

        fig_tech = px.bar(
            df_tech.head(20),
            x="count",
            y="skill",
            orientation="h",
            title=f"Top 20 des compétences techniques ({period_days} derniers jours)",
            labels={"count": "Nombre d'offres", "skill": "Compétence"},
            color="count",
            color_continuous_scale="Blues",
        )
        fig_tech.update_layout(height=600, showlegend=False)
        fig_tech.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_tech, use_container_width=True)

    with col2:
        st.markdown("**🥇 Top 10 compétences tech**")
        for i, skill in enumerate(tech_skills[:10], 1):
            st.markdown(f"{i}. **{skill['skill']}**")
            st.markdown(f"   {skill['count']} offres")
            st.markdown("")

    # Évolution des top compétences tech
    if tech_timeline:
        st.subheader("📈 Évolution des compétences techniques")

        data_for_tech = []
        for skill, timeline in tech_timeline.items():
            for entry in timeline:
                data_for_tech.append(
                    {"date": entry["date"], "skill": skill, "count": entry["count"]}
                )

        df_tech_timeline = pd.DataFrame(data_for_tech)
        df_tech_timeline["date"] = pd.to_datetime(df_tech_timeline["date"])

        fig_tech_trend = px.line(
            df_tech_timeline,
            x="date",
            y="count",
            color="skill",
            title=f"Évolution des 10 compétences techniques les plus demandées",
            labels={"date": "Date", "count": "Nombre d'offres", "skill": "Compétence"},
            markers=True,
        )

        fig_tech_trend.update_layout(
            height=500,
            hovermode="x unified",
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        )

        st.plotly_chart(fig_tech_trend, use_container_width=True)
else:
    st.info("Aucune donnée disponible pour les compétences techniques")

st.markdown("---")

# ============================================================================
# SECTION 3: SOFT SKILLS EN TENDANCE
# ============================================================================

st.header("🤝 Soft skills en tendance")

soft_skills = skill_data.get("soft_skills", [])
soft_timeline = skill_data.get("soft_timeline", {})

if soft_skills:
    col1, col2 = st.columns([2, 1])

    with col1:
        # Top soft skills
        df_soft = pd.DataFrame(soft_skills)

        fig_soft = px.bar(
            df_soft.head(15),
            x="count",
            y="skill",
            orientation="h",
            title=f"Top 15 des soft skills ({period_days} derniers jours)",
            labels={"count": "Nombre d'offres", "skill": "Compétence"},
            color="count",
            color_continuous_scale="Greens",
        )
        fig_soft.update_layout(height=500, showlegend=False)
        fig_soft.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_soft, use_container_width=True)

    with col2:
        st.markdown("**🌟 Top 10 soft skills**")
        for i, skill in enumerate(soft_skills[:10], 1):
            st.markdown(f"{i}. **{skill['skill']}**")
            st.markdown(f"   {skill['count']} offres")
            st.markdown("")

    # Évolution des top soft skills
    if soft_timeline:
        st.subheader("📈 Évolution des soft skills")

        data_for_soft = []
        for skill, timeline in soft_timeline.items():
            for entry in timeline:
                data_for_soft.append(
                    {"date": entry["date"], "skill": skill, "count": entry["count"]}
                )

        df_soft_timeline = pd.DataFrame(data_for_soft)
        df_soft_timeline["date"] = pd.to_datetime(df_soft_timeline["date"])

        fig_soft_trend = px.line(
            df_soft_timeline,
            x="date",
            y="count",
            color="skill",
            title=f"Évolution des 10 soft skills les plus demandées",
            labels={"date": "Date", "count": "Nombre d'offres", "skill": "Compétence"},
            markers=True,
        )

        fig_soft_trend.update_layout(
            height=500,
            hovermode="x unified",
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        )

        st.plotly_chart(fig_soft_trend, use_container_width=True)
else:
    st.info("Aucune donnée disponible pour les soft skills")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption(f"🔄 Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
