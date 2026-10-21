import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="World Data Completeness",
    page_icon="🌍",
    layout="wide"
)

# ---------- DESIGN ----------
st.markdown("""
<style>
.stApp {
    background-color: #10131f;
    color: #f4f4f8;
}
[data-testid="stSidebar"] {
    background-color: #191d2d;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
[data-testid="stMetric"] {
    background: #1c2234;
    border: 1px solid #343b52;
    padding: 16px;
    border-radius: 14px;
}
h1, h2, h3 {
    color: #f7f3ff;
}
</style>
""", unsafe_allow_html=True)

# ---------- LOAD DATA ----------
@st.cache_data
def load_data():
    countries = pd.read_csv("dashboard_data.csv")
    yearly = pd.read_csv("yearly_scores.csv")
    indicators = pd.read_csv("indicator_availability.csv")

    countries.columns = countries.columns.str.strip()
    yearly.columns = yearly.columns.str.strip()
    indicators.columns = indicators.columns.str.strip()

    for df in [countries, yearly, indicators]:
        if "Country Code" in df.columns:
            df["Country Code"] = df["Country Code"].astype(str).str.upper().str.strip()

    countries["DCS (%)"] = pd.to_numeric(
        countries["DCS (%)"], errors="coerce"
    )
    countries["Recent DCS (%)"] = pd.to_numeric(
        countries["Recent DCS (%)"], errors="coerce"
    )

    yearly["Year"] = pd.to_numeric(yearly["Year"], errors="coerce")
    if "DCS (%)" in yearly.columns:
        yearly["DCS (%)"] = pd.to_numeric(
            yearly["DCS (%)"], errors="coerce"
        )

    if "Value" in indicators.columns:
        indicators["Value"] = pd.to_numeric(
            indicators["Value"], errors="coerce"
        )

    return countries, yearly, indicators


try:
    countries, yearly, indicators = load_data()
except Exception as e:
    st.error(
        "Could not load the CSV files. Check that dashboard_data.csv, "
        "yearly_scores.csv and indicator_availability.csv are in the "
        "same GitHub folder as app.py."
    )
    st.exception(e)
    st.stop()


# ---------- COLUMN DETECTION ----------
def find_col(df, candidates):
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


region_col = find_col(countries, ["Region", "Region Name"])
income_col = find_col(countries, ["Income Level", "Income Group"])
indicator_name_col = find_col(
    indicators, ["Indicator Name", "Indicator", "Indicator_Name"]
)
available_col = find_col(
    indicators, ["Available", "Is Available", "Availability"]
)
value_col = find_col(indicators, ["Value"])
year_col = find_col(indicators, ["Year"])

# ---------- SIDEBAR ----------
st.sidebar.title("🌍 Data Explorer")
st.sidebar.caption("Explore data availability across economies, 2015–2024.")
st.sidebar.divider()

search = st.sidebar.text_input("🔎 Find a country")

filtered = countries.copy()

if region_col:
    regions = sorted(
        filtered[region_col].dropna().astype(str).unique().tolist()
    )
    selected_regions = st.sidebar.multiselect(
        "Filter by region", regions, default=regions
    )
    filtered = filtered[filtered[region_col].astype(str).isin(selected_regions)]

if income_col:
    incomes = sorted(
        filtered[income_col].dropna().astype(str).unique().tolist()
    )
    selected_incomes = st.sidebar.multiselect(
        "Filter by income group", incomes, default=incomes
    )
    filtered = filtered[filtered[income_col].astype(str).isin(selected_incomes)]

if search:
    filtered = filtered[
        filtered["Country"].astype(str).str.contains(
            search, case=False, na=False
        )
    ]

if filtered.empty:
    st.sidebar.warning("No countries match those filters.")
    st.stop()

country_options = sorted(filtered["Country"].dropna().astype(str).unique())
default_country = (
    "India" if "India" in country_options else country_options[0]
)

selected_country = st.sidebar.selectbox(
    "Choose a country",
    country_options,
    index=country_options.index(default_country)
)

st.sidebar.divider()
st.sidebar.markdown("### 🎨 Reading the map")
st.sidebar.markdown("""
- 🩷 **0–59%:** Low completeness
- 🟠 **60–79%:** Moderate completeness
- 🔴 **80–89%:** High, with gaps
- 🔵 **90–100%:** Very high completeness
""")
st.sidebar.caption(
    "DCS measures data availability, not data accuracy or trustworthiness."
)

# ---------- HEADER ----------
st.title("🌐 World Data Completeness Dashboard")
st.markdown(
    "### How complete is the world's public development data?"
)
st.caption(
    "World Bank indicators · 2015–2024 · "
    "Explore completeness, compare economies, and find missing data."
)

# ---------- OVERVIEW ----------
mean_dcs = countries["DCS (%)"].mean()
complete_count = (countries["DCS (%)"] == 100).sum()
incomplete_count = countries["DCS (%)"].lt(100).sum()

a, b, c, d = st.columns(4)
a.metric("Economies analysed", f"{len(countries):,}")
b.metric("Global average DCS", f"{mean_dcs:.1f}%")
c.metric("Fully complete", f"{complete_count}")
d.metric("With missing data", f"{incomplete_count}")

st.divider()

# ---------- MAP ----------
st.subheader("🗺️ Global completeness map")
st.write(
    "Hover over a country to inspect its score. "
    "Use the sidebar to filter countries and choose a profile."
)

map_data = filtered.dropna(subset=["Country Code", "DCS (%)"]).copy()

fig_map = px.choropleth(
    map_data,
    locations="Country Code",
    locationmode="ISO-3",
    color="DCS (%)",
    hover_name="Country",
    hover_data={
        "Country Code": True,
        "DCS (%)": ":.1f",
        "Available_Values": True,
        "Missing_Values": True
    },
    color_continuous_scale=[
        [0.00, "#f6b5d2"],
        [0.40, "#ff9f43"],
        [0.65, "#ef476f"],
        [0.82, "#4263eb"],
        [1.00, "#42d6c5"]
    ],
    range_color=(0, 100),
    labels={
        "DCS (%)": "Completeness (%)",
        "Available_Values": "Available values",
        "Missing_Values": "Missing values"
    }
)

fig_map.update_geos(
    showframe=False,
    showcoastlines=True,
    coastlinecolor="#5a6279",
    showland=True,
    landcolor="#252b3d",
    showocean=True,
    oceancolor="#141827",
    showcountries=True,
    countrycolor="#5a6279",
    projection_type="natural earth"
)

fig_map.update_layout(
    paper_bgcolor="#10131f",
    plot_bgcolor="#10131f",
    font_color="#f4f4f8",
    height=520,
    margin=dict(l=0, r=0, t=20, b=0),
    coloraxis_colorbar=dict(
        title="DCS (%)",
        tickvals=[0, 20, 40, 60, 80, 100],
        ticksuffix="%",
        tickfont=dict(color="#f4f4f8")
    )
)

st.plotly_chart(fig_map, use_container_width=True)

# ---------- SELECTED COUNTRY ----------
country_row = countries[
    countries["Country"].astype(str) == selected_country
].iloc[0]

country_code = str(country_row["Country Code"]).upper()
country_yearly = yearly[
    yearly["Country Code"] == country_code
].copy()

country_indicators = indicators[
    indicators["Country Code"] == country_code
].copy()

st.divider()
st.header(f"📍 {selected_country} — Country Profile")

if region_col:
    region_value = country_row.get(region_col, "Not available")
else:
    region_value = "Not available"

if income_col:
    income_value = country_row.get(income_col, "Not available")
else:
    income_value = "Not available"

st.caption(f"Region: {region_value}  ·  Income group: {income_value}")

available_values = country_row.get("Available_Values", None)
missing_values = country_row.get("Missing_Values", None)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Overall DCS", f"{country_row['DCS (%)']:.1f}%")
m2.metric(
    "Recent DCS",
    f"{country_row['Recent DCS (%)']:.1f}%"
    if pd.notna(country_row["Recent DCS (%)"]) else "N/A"
)
m3.metric(
    "Available values",
    f"{int(available_values)}" if pd.notna(available_values) else "N/A"
)
m4.metric(
    "Missing values",
    f"{int(missing_values)}" if pd.notna(missing_values) else "N/A"
)

# ---------- YEARLY TREND ----------
st.subheader("📈 Completeness over time")

if not country_yearly.empty and "DCS (%)" in country_yearly.columns:
    country_yearly = country_yearly.sort_values("Year")

    fig_year = px.line(
        country_yearly,
        x="Year",
        y="DCS (%)",
        markers=True,
        title=f"Annual DCS — {selected_country}",
        color_discrete_sequence=["#ff7eb6"],
        hover_data={"Year": True, "DCS (%)": ":.1f"}
    )

    fig_year.add_hline(
        y=mean_dcs,
        line_dash="dash",
        line_color="#42d6c5",
        annotation_text=f"All-country average: {mean_dcs:.1f}%"
    )

    fig_year.update_layout(
        paper_bgcolor="#10131f",
        plot_bgcolor="#191d2d",
        font_color="#f4f4f8",
        yaxis_title="Completeness (%)",
        xaxis_title="Year",
        yaxis=dict(range=[0, 105], ticksuffix="%"),
        margin=dict(l=10, r=10, t=60, b=10),
        legend_title=""
    )
    st.plotly_chart(fig_year, use_container_width=True)
else:
    st.info("Yearly DCS data is not available for this country.")

# ---------- INDICATOR COMPLETENESS ----------
st.subheader("🧩 Which indicators are missing data?")

if indicator_name_col and not country_indicators.empty:
    country_indicators["Year"] = pd.to_numeric(
        country_indicators["Year"], errors="coerce"
    )

    if available_col:
        country_indicators["_available"] = (
            country_indicators[available_col]
            .astype(str).str.lower()
            .isin(["true", "1", "yes"])
        )
    elif value_col:
        country_indicators["_available"] = country_indicators[value_col].notna()
    else:
        country_indicators["_available"] = country_indicators.notna().any(axis=1)

    indicator_summary = (
        country_indicators.groupby(indicator_name_col)
        .agg(
            Available_Years=("_available", "sum"),
            Total_Years=("Year", "count")
        )
        .reset_index()
    )
    indicator_summary["Completeness (%)"] = (
        indicator_summary["Available_Years"]
        / indicator_summary["Total_Years"].replace(0, pd.NA)
        * 100
    )
    indicator_summary["Missing_Years"] = (
        indicator_summary["Total_Years"]
        - indicator_summary["Available_Years"]
    )

    fig_ind = px.bar(
        indicator_summary.sort_values("Completeness (%)"),
        x="Completeness (%)",
        y=indicator_name_col,
        orientation="h",
        color="Completeness (%)",
        range_color=(0, 100),
        color_continuous_scale=[
            "#f6b5d2", "#ff9f43", "#ef476f", "#4263eb", "#42d6c5"
        ],
        hover_data={
            "Available_Years": True,
            "Missing_Years": True,
            "Completeness (%)": ":.1f"
        },
        title="Availability by indicator, across observed years"
    )
    fig_ind.update_layout(
        paper_bgcolor="#10131f",
        plot_bgcolor="#191d2d",
        font_color="#f4f4f8",
        xaxis=dict(range=[0, 100], ticksuffix="%"),
        yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=60, b=10)
    )
    st.plotly_chart(fig_ind, use_container_width=True)

    with st.expander("View indicator summary table"):
        st.dataframe(
            indicator_summary.rename(columns={
                indicator_name_col: "Indicator"
            }).sort_values("Completeness (%)", ascending=False),
            use_container_width=True,
            hide_index=True
        )
else:
    st.warning(
        "Could not identify the indicator-name column. "
        "Check the column names in indicator_availability.csv."
    )

# ---------- DETAILED RECORDS ----------
st.subheader("🔎 Inspect individual records")

if indicator_name_col and not country_indicators.empty:
    indicator_choices = sorted(
        country_indicators[indicator_name_col]
        .dropna().astype(str).unique().tolist()
    )
    chosen_indicator = st.selectbox(
        "Choose an indicator to inspect",
        indicator_choices
    )

    detail = country_indicators[
        country_indicators[indicator_name_col].astype(str) == chosen_indicator
    ].copy()

    display_cols = [
        c for c in [
            "Country", "Country Code", indicator_name_col,
            "Year", "Value", available_col
        ]
        if c and c in detail.columns
    ]

    detail = detail[display_cols].sort_values("Year")

    st.dataframe(
        detail.rename(columns={
            indicator_name_col: "Indicator",
            available_col: "Available"
        }),
        use_container_width=True,
        hide_index=True
    )

# ---------- GLOBAL COMPARISON ----------
st.divider()
st.subheader("🌍 How does this country compare?")

comparison = countries.copy()
comparison["Difference from global average"] = (
    comparison["DCS (%)"] - mean_dcs
)
comparison = comparison.sort_values("DCS (%)", ascending=False)

st.write(
    f"**{selected_country}:** {country_row['DCS (%)']:.1f}%  ·  "
    f"**Global average:** {mean_dcs:.1f}%  ·  "
    f"**Difference:** "
    f"{country_row['DCS (%)'] - mean_dcs:+.1f} percentage points"
)

top, bottom = st.columns(2)

with top:
    st.markdown("#### Highest completeness")
    st.dataframe(
        comparison[["Country", "DCS (%)"]].head(5),
        hide_index=True,
        use_container_width=True
    )

with bottom:
    st.markdown("#### Lowest completeness")
    st.dataframe(
        comparison[["Country", "DCS (%)"]].tail(5)
        .sort_values("DCS (%)"),
        hide_index=True,
        use_container_width=True
    )

# ---------- METHODOLOGY ----------
with st.expander("ℹ️ Methodology and interpretation"):
    st.markdown("""
    **Data Completeness Score (DCS)** measures the share of expected
    indicator-year values that are available.

    - Overall score: available values divided by 70 expected values,
      multiplied by 100.
    - Annual score: available values divided by 7 expected indicators,
      multiplied by 100.
    - Recent DCS: availability across 2022–2024.
    - Missing data is not automatically evidence of poor data quality.
    - Completeness measures availability, not accuracy, reliability,
      or trustworthiness.

    Scores and comparisons are descriptive, not causal.
    """)

st.caption(
    "Data source: World Bank indicators. "
    "Dashboard prepared for educational and analytical exploration."
)
