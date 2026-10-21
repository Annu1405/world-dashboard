import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="World Data Completeness",
    page_icon="🌍",
    layout="wide"
)

# ---------------- DESIGN ----------------
st.markdown("""
<style>
.stApp {
    background-color: #10131F;
    color: #F5F5FA;
}
[data-testid="stSidebar"] {
    background-color: #191D2D;
}
[data-testid="stMetric"] {
    background: #1C2234;
    border: 1px solid #343B52;
    padding: 15px;
    border-radius: 14px;
}
h1, h2, h3 {
    color: #F7F3FF;
}
</style>
""", unsafe_allow_html=True)

PALETTE = {
    "Below 30%": "#E63946",
    "30–59%": "#F6B5D2",
    "60–79%": "#FF9F43",
    "80–89%": "#9B5DE5",
    "90–100%": "#4263EB"
}

BANDS = list(PALETTE.keys())


def get_band(score):
    if pd.isna(score):
        return "Unknown"
    if score < 30:
        return "Below 30%"
    if score < 60:
        return "30–59%"
    if score < 80:
        return "60–79%"
    if score < 90:
        return "80–89%"
    return "90–100%"


# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    countries = pd.read_csv("dashboard_data.csv")
    yearly = pd.read_csv("yearly_scores.csv")
    indicators = pd.read_csv("indicator_availability.csv")

    for df in [countries, yearly, indicators]:
        df.columns = df.columns.str.strip()
        if "Country Code" in df.columns:
            df["Country Code"] = (
                df["Country Code"].astype(str).str.upper().str.strip()
            )

    countries["DCS (%)"] = pd.to_numeric(
        countries["DCS (%)"], errors="coerce"
    )
    countries["Recent DCS (%)"] = pd.to_numeric(
        countries["Recent DCS (%)"], errors="coerce"
    )

    if "Year" in yearly:
        yearly["Year"] = pd.to_numeric(yearly["Year"], errors="coerce")
    if "DCS (%)" in yearly:
        yearly["DCS (%)"] = pd.to_numeric(
            yearly["DCS (%)"], errors="coerce"
        )
    if "Value" in indicators:
        indicators["Value"] = pd.to_numeric(
            indicators["Value"], errors="coerce"
        )

    return countries, yearly, indicators


try:
    countries, yearly, indicators = load_data()
except Exception as error:
    st.error(
        "Could not load the CSV files. Make sure these files are in "
        "the same GitHub folder as app.py: dashboard_data.csv, "
        "yearly_scores.csv, indicator_availability.csv."
    )
    st.exception(error)
    st.stop()


def find_col(df, candidates):
    return next((c for c in candidates if c in df.columns), None)


region_col = find_col(countries, ["Region", "Region Name"])
income_col = find_col(countries, ["Income Level", "Income Group"])
indicator_col = find_col(
    indicators, ["Indicator Name", "Indicator", "Indicator_Name"]
)
available_col = find_col(
    indicators, ["Available", "Is Available", "Availability"]
)

countries["Completeness Band"] = countries["DCS (%)"].apply(get_band)

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.title("🌍 Data Explorer")
st.sidebar.caption("Explore 217 economies and their data availability.")

search = st.sidebar.text_input("🔎 Search country")

filtered = countries.copy()

if region_col:
    regions = sorted(filtered[region_col].dropna().astype(str).unique())
    selected_regions = st.sidebar.multiselect(
        "Region", regions, default=regions
    )
    filtered = filtered[
        filtered[region_col].astype(str).isin(selected_regions)
    ]

if income_col:
    income_groups = sorted(
        filtered[income_col].dropna().astype(str).unique()
    )
    selected_income = st.sidebar.multiselect(
        "Income group", income_groups, default=income_groups
    )
    filtered = filtered[
        filtered[income_col].astype(str).isin(selected_income)
    ]

if search:
    filtered = filtered[
        filtered["Country"].astype(str).str.contains(
            search, case=False, na=False
        )
    ]

# Persist the clicked coverage band across reruns.
if "coverage_band" not in st.session_state:
    st.session_state.coverage_band = "All countries"

# ---------------- HEADER ----------------
st.title("🌐 World Data Completeness Dashboard")
st.write(
    "Explore where World Bank indicator data is available, "
    "where gaps remain, and how economies compare."
)
st.caption(
    "2015–2024 | Data Completeness Score (DCS) measures availability, "
    "not accuracy or trustworthiness."
)

mean_dcs = countries["DCS (%)"].mean()
complete = int((countries["DCS (%)"] == 100).sum())
incomplete = int((countries["DCS (%)"] < 100).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Economies", len(countries))
m2.metric("Global average DCS", f"{mean_dcs:.1f}%")
m3.metric("100% complete", complete)
m4.metric("With missing data", incomplete)

st.divider()

# ---------------- CLICKABLE MAP ----------------
st.subheader("🗺️ Global completeness map")
st.caption(
    "Hover for country details. Click a country to open its profile."
)

map_data = filtered.copy()

active_band = st.session_state.coverage_band
if active_band != "All countries":
    map_data = map_data[
        map_data["Completeness Band"] == active_band
    ]

map_data = map_data.dropna(subset=["Country Code", "DCS (%)"])

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
        "Missing_Values": True,
        "Completeness Band": True
    },
    color_continuous_scale=[
        [0.00, "#E63946"],
        [0.30, "#F6B5D2"],
        [0.60, "#FF9F43"],
        [0.80, "#9B5DE5"],
        [1.00, "#4263EB"]
    ],
    range_color=(0, 100),
    labels={
        "DCS (%)": "Completeness",
        "Available_Values": "Available values",
        "Missing_Values": "Missing values"
    }
)

fig_map.update_geos(
    projection_type="natural earth",
    showframe=False,
    showcoastlines=True,
    coastlinecolor="#687089",
    showland=True,
    landcolor="#252B3D",
    showocean=True,
    oceancolor="#141827",
    showcountries=True,
    countrycolor="#687089"
)

fig_map.update_layout(
    paper_bgcolor="#10131F",
    plot_bgcolor="#10131F",
    font_color="#F5F5FA",
    height=500,
    margin=dict(l=0, r=0, t=20, b=0),
    coloraxis_colorbar=dict(
        title="DCS (%)",
        tickvals=[0, 30, 60, 80, 90, 100],
        ticksuffix="%"
    )
)

map_event = st.plotly_chart(
    fig_map,
    use_container_width=True,
    key="world_map",
    on_select="rerun",
    selection_mode="points"
)

# Update country selection from a map click.
if map_event and map_event.selection.points:
    clicked_point = map_event.selection.points[0]
    clicked_code = clicked_point.get("location")

    if clicked_code:
        matches = countries[
            countries["Country Code"] == str(clicked_code).upper()
        ]
        if not matches.empty:
            st.session_state["selected_country"] = matches.iloc[0]["Country"]

# ---------------- CLICKABLE COVERAGE PIE ----------------
st.divider()
st.subheader("🍩 How complete is the world's data?")
st.caption(
    "Click a slice to filter the country list and map. "
    "Select the slice again or clear the filter to reset."
)

band_counts = (
    countries[countries["Completeness Band"].isin(BANDS)]
    ["Completeness Band"]
    .value_counts()
    .reindex(BANDS, fill_value=0)
    .rename_axis("Band")
    .reset_index(name="Countries")
)

pie_fig = px.pie(
    band_counts,
    names="Band",
    values="Countries",
    hole=0.48,
    color="Band",
    color_discrete_map=PALETTE,
    custom_data=["Band"]
)

pie_fig.update_traces(
    textposition="inside",
    textinfo="label+value+percent",
    hovertemplate=(
        "<b>%{label}</b><br>"
        "Countries: %{value}<br>"
        "Share: %{percent}<extra></extra>"
    )
)

pie_fig.update_layout(
    paper_bgcolor="#10131F",
    font_color="#F5F5FA",
    height=390,
    margin=dict(l=10, r=10, t=20, b=20),
    showlegend=False
)

pie_event = st.plotly_chart(
    pie_fig,
    use_container_width=True,
    key="coverage_pie",
    on_select="rerun",
    selection_mode="points"
)

if pie_event and pie_event.selection.points:
    point = pie_event.selection.points[0]
    clicked_band = point.get("label")

    if clicked_band in BANDS:
        if st.session_state.coverage_band == clicked_band:
            st.session_state.coverage_band = "All countries"
        else:
            st.session_state.coverage_band = clicked_band

if st.session_state.coverage_band != "All countries":
    st.info(f"Showing countries in the **{st.session_state.coverage_band}** band.")

    if st.button("Clear completeness filter"):
        st.session_state.coverage_band = "All countries"
        st.rerun()

# ---------------- COUNTRY LIST ----------------
visible_countries = filtered.copy()

if st.session_state.coverage_band != "All countries":
    visible_countries = visible_countries[
        visible_countries["Completeness Band"]
        == st.session_state.coverage_band
    ]

st.markdown("#### Countries in this group")

if visible_countries.empty:
    st.warning("No countries match the current filters.")
else:
    st.dataframe(
        visible_countries[
            ["Country", "DCS (%)", "Available_Values",
             "Missing_Values", "Completeness Band"]
        ].sort_values("DCS (%)"),
        use_container_width=True,
        hide_index=True
    )

# ---------------- COUNTRY PROFILE ----------------
st.divider()
st.header("📍 Country profile")

available_country_names = sorted(
    visible_countries["Country"].dropna().astype(str).unique()
)

if not available_country_names:
    st.info("Clear or adjust filters to view a country profile.")
    st.stop()

if (
    "selected_country" not in st.session_state
    or st.session_state.selected_country not in available_country_names
):
    st.session_state.selected_country = (
        "India" if "India" in available_country_names
        else available_country_names[0]
    )

selected_country = st.sidebar.selectbox(
    "Country profile",
    available_country_names,
    key="selected_country"
)

row = countries[countries["Country"] == selected_country].iloc[0]
code = row["Country Code"]

region = row.get(region_col, "Not available") if region_col else "Not available"
income = row.get(income_col, "Not available") if income_col else "Not available"

st.subheader(selected_country)
st.caption(f"Region: {region}  ·  Income group: {income}")

a, b, c, d = st.columns(4)
a.metric("Overall DCS", f"{row['DCS (%)']:.1f}%")
b.metric(
    "Recent DCS",
    f"{row['Recent DCS (%)']:.1f}%"
    if pd.notna(row["Recent DCS (%)"]) else "N/A"
)
c.metric("Available values", int(row["Available_Values"]))
d.metric("Missing values", int(row["Missing_Values"]))

# ---------------- YEARLY TREND ----------------
st.subheader("📈 Annual completeness")

country_yearly = yearly[yearly["Country Code"] == code].copy()

if not country_yearly.empty and "DCS (%)" in country_yearly:
    country_yearly = country_yearly.sort_values("Year")

    line_fig = px.line(
        country_yearly,
        x="Year",
        y="DCS (%)",
        markers=True,
        color_discrete_sequence=["#F6B5D2"],
        hover_data={"Year": True, "DCS (%)": ":.1f"}
    )

    line_fig.add_hline(
        y=mean_dcs,
        line_dash="dash",
        line_color="#42D6C5",
        annotation_text=f"Global average: {mean_dcs:.1f}%"
    )

    line_fig.update_layout(
        paper_bgcolor="#10131F",
        plot_bgcolor="#191D2D",
        font_color="#F5F5FA",
        yaxis_title="DCS (%)",
        xaxis_title="Year",
        yaxis=dict(range=[0, 105], ticksuffix="%")
    )
    st.plotly_chart(line_fig, use_container_width=True)
else:
    st.info("Yearly scores are unavailable for this country.")

# ---------------- INDICATOR SUMMARY ----------------
st.subheader("🧩 Indicator availability")

country_indicators = indicators[
    indicators["Country Code"] == code
].copy()

if indicator_col and not country_indicators.empty:
    if available_col:
        country_indicators["_available"] = (
            country_indicators[available_col]
            .astype(str).str.lower()
            .isin(["true", "1", "yes"])
        )
    elif "Value" in country_indicators:
        country_indicators["_available"] = (
            country_indicators["Value"].notna()
        )
    else:
        country_indicators["_available"] = False

    if "Year" in country_indicators:
        summary = (
            country_indicators.groupby(indicator_col)
            .agg(
                Available_Years=("_available", "sum"),
                Total_Years=("Year", "count")
            )
            .reset_index()
        )
        summary["Missing_Years"] = (
            summary["Total_Years"] - summary["Available_Years"]
        )
        summary["Completeness (%)"] = (
            summary["Available_Years"]
            / summary["Total_Years"].replace(0, pd.NA) * 100
        )

        bar_fig = px.bar(
            summary.sort_values("Completeness (%)"),
            x="Completeness (%)",
            y=indicator_col,
            orientation="h",
            color="Completeness (%)",
            color_continuous_scale=[
                "#E63946", "#F6B5D2", "#FF9F43", "#9B5DE5", "#4263EB"
            ],
            range_color=(0, 100),
            hover_data=[
                "Available_Years", "Missing_Years", "Total_Years"
            ]
        )
        bar_fig.update_layout(
            paper_bgcolor="#10131F",
            plot_bgcolor="#191D2D",
            font_color="#F5F5FA",
            xaxis=dict(range=[0, 100], ticksuffix="%"),
            yaxis_title="",
            coloraxis_showscale=False
        )
        st.plotly_chart(bar_fig, use_container_width=True)

        with st.expander("View indicator summary"):
            st.dataframe(
                summary.rename(columns={indicator_col: "Indicator"}),
                use_container_width=True,
                hide_index=True
            )

# ---------------- METHODOLOGY ----------------
with st.expander("ℹ️ How to interpret the scores"):
    st.markdown("""
    - **Overall DCS:** available indicator-year values out of 70 expected.
    - **Annual DCS:** available indicators out of 7 expected each year.
    - **Recent DCS:** completeness across 2022–2024.
    - Missing values indicate unavailable data, not necessarily poor quality.
    - A flat 100% line is valid when all seven indicators are available
      in every year.
    - The map colours use a fixed scale so countries can be compared fairly.
    """)

st.caption(
    "Source: World Bank indicators | Data completeness measures availability, "
    "not accuracy or trustworthiness."
)
