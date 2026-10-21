import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="World Data Completeness",
    page_icon="🌍",
    layout="wide"
)

# ---------------- DESIGN ----------------
st.markdown("""
<style>
.stApp { background:#10131F; color:#F5F5FA; }
[data-testid="stSidebar"] { background:#191D2D; }
[data-testid="stMetric"] {
    background:#1C2234;
    border:1px solid #343B52;
    padding:14px;
    border-radius:14px;
}
h1,h2,h3 { color:#F7F3FF; }
</style>
""", unsafe_allow_html=True)

COLORS = {
    "Below 30%": "#E63946",
    "30–59%": "#F6B5D2",
    "60–79%": "#FF9F43",
    "80–89%": "#9B5DE5",
    "90–100%": "#4263EB",
    "Unknown": "#777777"
}
BANDS = list(COLORS.keys())[:-1]


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


def find_col(df, choices):
    for col in choices:
        if col in df.columns:
            return col
    return None


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

    for col in [
        "DCS (%)", "Recent DCS (%)",
        "Available_Values", "Missing_Values"
    ]:
        if col in countries.columns:
            countries[col] = pd.to_numeric(
                countries[col], errors="coerce"
            )

    for df in [yearly, indicators]:
        if "Year" in df.columns:
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

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
        "Could not load the CSV files. Make sure these three files "
        "are in the same repository folder as app.py: "
        "dashboard_data.csv, yearly_scores.csv, "
        "indicator_availability.csv."
    )
    st.exception(e)
    st.stop()

required = ["Country", "Country Code", "DCS (%)"]
missing = [col for col in required if col not in countries.columns]

if missing:
    st.error(f"Missing columns in dashboard_data.csv: {missing}")
    st.stop()

countries = countries.dropna(
    subset=["Country", "Country Code", "DCS (%)"]
).copy()

countries["Country"] = countries["Country"].astype(str).str.strip()
countries["Country Code"] = (
    countries["Country Code"].astype(str).str.upper().str.strip()
)
countries["Completeness Band"] = countries["DCS (%)"].apply(get_band)

region_col = find_col(countries, ["Region", "Region Name"])
income_col = find_col(countries, ["Income Level", "Income Group"])
indicator_col = find_col(
    indicators, ["Indicator Name", "Indicator", "Indicator_Name"]
)
available_col = find_col(
    indicators, ["Available", "Is Available", "Availability"]
)

# ---------------- STATE ----------------
if "selected_country" not in st.session_state:
    st.session_state.selected_country = (
        "India" if "India" in countries["Country"].values
        else countries.iloc[0]["Country"]
    )

if "sidebar_country" not in st.session_state:
    st.session_state.sidebar_country = st.session_state.selected_country

if "coverage_band" not in st.session_state:
    st.session_state.coverage_band = "All countries"

# Apply country selection before creating the sidebar widget.
if "pending_country" in st.session_state:
    pending = st.session_state.pop("pending_country")
    if pending in countries["Country"].values:
        st.session_state.selected_country = pending
        st.session_state.sidebar_country = pending

# ---------------- SIDEBAR ----------------
st.sidebar.title("🌍 Data Explorer")
st.sidebar.caption("Search, filter and explore economies.")

search = st.sidebar.text_input("🔎 Search country")
filtered = countries.copy()

if region_col:
    regions = sorted(filtered[region_col].dropna().astype(str).unique())
    chosen_regions = st.sidebar.multiselect(
        "Region", regions, default=regions
    )
    filtered = filtered[
        filtered[region_col].astype(str).isin(chosen_regions)
    ]

if income_col:
    incomes = sorted(filtered[income_col].dropna().astype(str).unique())
    chosen_incomes = st.sidebar.multiselect(
        "Income group", incomes, default=incomes
    )
    filtered = filtered[
        filtered[income_col].astype(str).isin(chosen_incomes)
    ]

if search:
    filtered = filtered[
        filtered["Country"].str.contains(
            search, case=False, na=False, regex=False
        )
    ]

if filtered.empty:
    st.warning("No countries match these filters.")
    st.stop()

country_options = sorted(filtered["Country"].unique())

if st.session_state.sidebar_country not in country_options:
    st.session_state.sidebar_country = (
        "India" if "India" in country_options else country_options[0]
    )

st.sidebar.selectbox(
    "Choose a country (type to search)",
    country_options,
    key="sidebar_country"
)
st.session_state.selected_country = st.session_state.sidebar_country

st.sidebar.divider()
st.sidebar.markdown("### 🎨 Map colour guide")
for band, colour in COLORS.items():
    if band != "Unknown":
        st.sidebar.markdown(
            f'<span style="color:{colour};font-size:20px">●</span> {band}',
            unsafe_allow_html=True
        )
st.sidebar.caption("DCS measures availability, not accuracy.")

# ---------------- HEADER AND KPIs ----------------
st.title("🌐 World Data Completeness Dashboard")
st.write(
    "Explore data availability, compare economies, and discover "
    "where development indicators have missing values."
)
st.caption("World Bank indicators · 2015–2024")

global_mean = countries["DCS (%)"].mean()
best_country = countries.loc[countries["DCS (%)"].idxmax()]
worst_country = countries.loc[countries["DCS (%)"].idxmin()]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Economies", len(countries))
k2.metric("Global average DCS", f"{global_mean:.1f}%")
k3.metric("100% complete", int((countries["DCS (%)"] == 100).sum()))
k4.metric("With missing data", int((countries["DCS (%)"] < 100).sum()))

st.divider()

# =========================================================
# 1. WORLD MAP FIRST
# =========================================================
st.subheader("🗺️ Interactive world map")
st.caption(
    "Hover for details. Click a country to update its profile. "
    "The selected country is outlined in white."
)

map_data = filtered.copy()
if st.session_state.coverage_band != "All countries":
    map_data = map_data[
        map_data["Completeness Band"] == st.session_state.coverage_band
    ]

if map_data.empty:
    st.warning("No countries match the current filters and score group.")
else:
    selected_rows = countries[
        countries["Country"] == st.session_state.selected_country
    ]
    selected_code = (
        selected_rows.iloc[0]["Country Code"]
        if not selected_rows.empty else None
    )

    fig_map = px.choropleth(
        map_data,
        locations="Country Code",
        locationmode="ISO-3",
        color="DCS (%)",
        hover_name="Country",
        hover_data={
            "Country Code": True,
            "DCS (%)": ":.1f",
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
        labels={"DCS (%)": "Completeness"}
    )

    if selected_code and selected_code in map_data["Country Code"].values:
        fig_map.add_trace(go.Choropleth(
            locations=[selected_code],
            z=[1],
            locationmode="ISO-3",
            colorscale=[
                [0, "rgba(0,0,0,0)"],
                [1, "rgba(0,0,0,0)"]
            ],
            showscale=False,
            marker_line_color="#FFFFFF",
            marker_line_width=2.5,
            hoverinfo="skip",
            showlegend=False
        ))

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

    if map_event and map_event.selection.points:
        point = map_event.selection.points[0]
        clicked_code = point.get("location")

        if clicked_code:
            match = countries[
                countries["Country Code"] == str(clicked_code).upper()
            ]
            if not match.empty:
                clicked_country = match.iloc[0]["Country"]
                if clicked_country != st.session_state.selected_country:
                    st.session_state["pending_country"] = clicked_country
                    st.rerun()

# =========================================================
# 2. PIE CHART AND COUNTRY LIST
# =========================================================
st.divider()
st.subheader("🍩 Global completeness groups")
st.caption("Click a slice to see the countries in that score range.")

band_counts = (
    countries[countries["Completeness Band"].isin(BANDS)]
    .groupby("Completeness Band")
    .size()
    .reindex(BANDS, fill_value=0)
    .rename("Countries")
    .reset_index()
)

pie = px.pie(
    band_counts,
    names="Completeness Band",
    values="Countries",
    hole=0.48,
    color="Completeness Band",
    color_discrete_map=COLORS,
    category_orders={"Completeness Band": BANDS}
)
pie.update_traces(
    textinfo="label+value+percent",
    hovertemplate=(
        "<b>%{label}</b><br>Countries: %{value}<br>"
        "Share: %{percent}<extra></extra>"
    )
)
pie.update_layout(
    paper_bgcolor="#10131F",
    font_color="#F5F5FA",
    height=410,
    margin=dict(l=10, r=10, t=25, b=10),
    showlegend=False
)

pie_col, list_col = st.columns([1, 1.2])

with pie_col:
    pie_event = st.plotly_chart(
        pie,
        use_container_width=True,
        key="coverage_pie",
        on_select="rerun",
        selection_mode="points"
    )

if pie_event and pie_event.selection.points:
    point = pie_event.selection.points[0]
    band_clicked = point.get("label")

    if band_clicked not in BANDS:
        index = point.get("point_index", point.get("point_number"))
        if index is not None and 0 <= index < len(band_counts):
            band_clicked = band_counts.iloc[index]["Completeness Band"]

    if band_clicked in BANDS:
        previous_band = st.session_state.get("last_pie_band")
        if band_clicked != previous_band:
            st.session_state.coverage_band = band_clicked
            st.session_state.last_pie_band = band_clicked

with list_col:
    st.markdown("#### Countries in selected group")
    current_band = st.session_state.coverage_band

    if current_band == "All countries":
        st.info("Click a pie slice to see its countries.")
    else:
        st.markdown(f"**{current_band}**")
        group = countries[
            countries["Completeness Band"] == current_band
        ].sort_values(["DCS (%)", "Country"])

        st.caption(f"{len(group)} countries in this group")

        if not group.empty:
            country_to_open = st.selectbox(
                "Select a country from this group",
                group["Country"].tolist(),
                key=f"pie_country_{current_band}"
            )

            if st.button("Open this country", key="open_pie_country",
                         use_container_width=True):
                st.session_state["pending_country"] = country_to_open
                st.rerun()

    if st.button("Clear pie filter", key="clear_pie_filter",
                 use_container_width=True):
        st.session_state.coverage_band = "All countries"
        st.session_state.pop("last_pie_band", None)
        st.rerun()

# =========================================================
# 3. COUNTRY PROFILE
# =========================================================
st.divider()

country_matches = countries[
    countries["Country"] == st.session_state.selected_country
]
if country_matches.empty:
    st.warning("The selected country is not available in the dataset.")
    st.stop()

country = country_matches.iloc[0]
code = country["Country Code"]

st.header(f"📍 {country['Country']} — Country Profile")

region = country.get(region_col, "Not available") if region_col else "Not available"
income = country.get(income_col, "Not available") if income_col else "Not available"
st.caption(f"Region: {region} · Income group: {income}")

a, b, c, d = st.columns(4)
a.metric("Overall DCS", f"{country['DCS (%)']:.1f}%")

recent = country.get("Recent DCS (%)", float("nan"))
b.metric("Recent DCS", f"{recent:.1f}%" if pd.notna(recent) else "N/A")

available_values = country.get("Available_Values", float("nan"))
missing_values = country.get("Missing_Values", float("nan"))
c.metric("Available values", int(available_values) if pd.notna(available_values) else "N/A")
d.metric("Missing values", int(missing_values) if pd.notna(missing_values) else "N/A")

# =========================================================
# 4. YEARLY TREND
# =========================================================
st.subheader("📈 Annual completeness")
country_yearly = yearly[yearly["Country Code"] == code].copy()

if not country_yearly.empty and "DCS (%)" in country_yearly.columns:
    country_yearly = country_yearly.dropna(
        subset=["Year", "DCS (%)"]
    ).sort_values("Year")

    line = px.line(
        country_yearly,
        x="Year",
        y="DCS (%)",
        markers=True,
        color_discrete_sequence=["#F6B5D2"],
        hover_data={"Year": True, "DCS (%)": ":.1f"}
    )
    line.add_hline(
        y=global_mean,
        line_dash="dash",
        line_color="#42D6C5",
        annotation_text=f"Global average: {global_mean:.1f}%"
    )
    line.update_layout(
        paper_bgcolor="#10131F",
        plot_bgcolor="#191D2D",
        font_color="#F5F5FA",
        yaxis=dict(range=[0, 105], ticksuffix="%"),
        xaxis_title="Year",
        yaxis_title="DCS (%)"
    )
    st.plotly_chart(line, use_container_width=True, key="yearly_trend")
else:
    st.info("Yearly scores are unavailable for this country.")

# =========================================================
# 5. INDICATOR AVAILABILITY
# =========================================================
st.subheader("🧩 Indicator availability")
country_indicators = indicators[indicators["Country Code"] == code].copy()

if indicator_col and not country_indicators.empty and "Year" in country_indicators.columns:
    if available_col:
        country_indicators["_available"] = (
            country_indicators[available_col]
            .astype(str).str.lower().isin(["true", "1", "yes"])
        )
    elif "Value" in country_indicators.columns:
        country_indicators["_available"] = country_indicators["Value"].notna()
    else:
        country_indicators["_available"] = False

    summary = (
        country_indicators.groupby(indicator_col)
        .agg(
            Available_Years=("_available", "sum"),
            Total_Years=("Year", "count")
        )
        .reset_index()
    )
    summary["Missing_Years"] = summary["Total_Years"] - summary["Available_Years"]
    summary["Completeness (%)"] = (
        summary["Available_Years"]
        / summary["Total_Years"].replace(0, pd.NA) * 100
    )

    bar = px.bar(
        summary.sort_values("Completeness (%)"),
        x="Completeness (%)",
        y=indicator_col,
        orientation="h",
        color="Completeness (%)",
        color_continuous_scale=["#E63946", "#FF9F43", "#9B5DE5", "#4263EB"],
        range_color=(0, 100),
        hover_data=["Available_Years", "Missing_Years", "Total_Years"]
    )
    bar.update_layout(
        paper_bgcolor="#10131F",
        plot_bgcolor="#191D2D",
        font_color="#F5F5FA",
        xaxis=dict(range=[0, 100], ticksuffix="%"),
        yaxis_title="",
        coloraxis_showscale=False
    )
    st.plotly_chart(bar, use_container_width=True, key="indicator_chart")

    with st.expander("View indicator summary"):
        st.dataframe(
            summary.rename(columns={indicator_col: "Indicator"}),
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("Indicator-level data is unavailable for this country.")

# =========================================================
# 6. HIGHEST AND LOWEST COMPARATOR
# =========================================================
st.divider()
st.header("⚖️ Country comparator")
st.caption("Compare the most complete country with the lowest-scoring country.")

left, right = st.columns(2)

with left:
    st.markdown("#### 🏆 Highest completeness")
    st.subheader(best_country["Country"])
    st.metric("DCS", f"{best_country['DCS (%)']:.1f}%")

with right:
    st.markdown("#### 🔎 Lowest completeness")
    st.subheader(worst_country["Country"])
    st.metric("DCS", f"{worst_country['DCS (%)']:.1f}%")

gap = best_country["DCS (%)"] - worst_country["DCS (%)"]
st.info(
    f"The gap between the highest and lowest scores is "
    f"**{gap:.1f} percentage points**."
)

with st.expander("ℹ️ Methodology"):
    st.markdown("""
    - Overall DCS = available values divided by 70 expected
      indicator-year values.
    - Annual DCS = available indicators divided by 7 expected indicators.
    - Recent DCS covers 2022–2024.
    - Missing data does not automatically mean poor-quality data.
    - The map uses a fixed 0–100% scale for fair comparisons.
    """)

st.caption(
    "Source: World Bank indicators. DCS measures availability, "
    "not accuracy or trustworthiness."
)
