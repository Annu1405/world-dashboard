import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="World Bank Data Completeness Dashboard",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 World Bank Data Completeness Dashboard")
st.caption("Exploring data availability across economies, 2015–2024")

@st.cache_data
def load_data():
    countries = pd.read_csv("dashboard_data.csv")
    yearly = pd.read_csv("yearly_scores.csv")
    indicators = pd.read_csv("indicator_availability.csv")
    return countries, yearly, indicators

countries, yearly, indicators = load_data()

st.sidebar.header("Explore the data")
country_name = st.sidebar.selectbox(
    "Choose a country",
    sorted(countries["Country"].dropna().unique())
)

selected = countries[countries["Country"] == country_name].iloc[0]
country_code = selected["Country Code"]

# Summary cards
a, b, c = st.columns(3)
a.metric("Overall DCS", f'{selected["DCS (%)"]:.2f}%')
b.metric("Available values", int(selected["Available_Values"]))
c.metric("Missing values", int(selected["Missing_Values"]))

st.metric("Recent DCS (2022–2024)", f'{selected["Recent DCS (%)"]:.2f}%')

# World map
st.subheader("Global data completeness")
fig_map = px.choropleth(
    countries,
    locations="Country Code",
    color="DCS (%)",
    hover_name="Country",
    hover_data={
        "Country Code": True,
        "DCS (%)": ":.2f",
        "Available_Values": True,
        "Missing_Values": True
    },
    color_continuous_scale="YlGnBu",
    range_color=(0, 100),
    title="Data Completeness Score by country"
)
fig_map.update_layout(margin=dict(l=0, r=0, t=50, b=0))
st.plotly_chart(fig_map, use_container_width=True)

# Yearly trend
st.subheader(f"Yearly completeness — {country_name}")
country_yearly = yearly[yearly["Country Code"] == country_code].sort_values("Year")
fig_year = px.line(
    country_yearly,
    x="Year",
    y="Yearly DCS (%)",
    markers=True,
    range_y=[0, 100],
    labels={"Yearly DCS (%)": "Data Completeness Score (%)"}
)
st.plotly_chart(fig_year, use_container_width=True)

# Indicator details
st.subheader(f"Indicator availability — {country_name}")
country_indicators = indicators[
    indicators["Country Code"] == country_code
].copy()

indicator_summary = country_indicators.groupby("Indicator").agg(
    Available=("Available", "sum"),
    Expected=("Available", "size")
).reset_index()
indicator_summary["Availability (%)"] = (
    indicator_summary["Available"] /
    indicator_summary["Expected"] * 100
).round(2)

fig_ind = px.bar(
    indicator_summary.sort_values("Availability (%)"),
    x="Availability (%)",
    y="Indicator",
    orientation="h",
    range_x=[0, 100],
    labels={"Availability (%)": "Available years (%)"}
)
st.plotly_chart(fig_ind, use_container_width=True)

# Actual values and missing years
st.subheader("Indicator records")
st.dataframe(
    country_indicators[
        ["Indicator", "Year", "Value", "Available"]
    ].sort_values(["Indicator", "Year"]),
    use_container_width=True,
    hide_index=True
)

st.caption(
    "DCS measures data availability, not accuracy or trustworthiness. "
    "Source: World Bank indicators, 2015–2024."
)

