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
.stApp {background:#10131F;color:#F5F5FA;}
[data-testid="stSidebar"] {background:#191D2D;}
[data-testid="stMetric"] {
    background:#1C2234;
    border:1px solid #343B52;
    padding:14px;
    border-radius:14px;
}
h1,h2,h3 {color:#F7F3FF;}
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


def find_col(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None


# ---------------- DATA ----------------
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
        "Could not load the CSV files. Ensure these files are beside app.py: "
        "dashboard_data.csv, yearly_scores.csv, indicator_availability.csv."
    )
    st.exception(e)
    st.stop()

required = ["Country", "Country Code", "DCS (%)"]
missing = [c for c in required if c not in countries.columns]
if missing:
    st.error(f"Missing columns in dashboard_data.csv: {missing}")
    st.stop()

countries = countries.dropna(
    subset=["Country", "Country Code", "DCS (%)"]
).copy()
countries["Country"] = countries["Country"].astype(str).str.strip()
countries["Country Code"] = countries["Country Code"].astype(str).str.upper()
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

if "coverage_band" not in st.session_state:
    st.session_state.coverage_band = "All countries"

# Handle pending selections before the relevant widgets are created.
if "pending_country" in st.session_state:
    pending = st.session_state.pop("pending_country")
    if pending in countries["Country"].values:
        st.session_state.selected_country = pending

if "pending_band" in st.session_state:
    pending_band = st.session_state.pop("pending_band")
    if pending_band in BANDS or pending_band == "All countries":
        st.session_state.coverage_band = pending_band

# ---------------- SIDEBAR ----------------
st.sidebar.title("🌍 Data Explorer")
st.sidebar.caption("Search, filter and explore economies.")

search = st.sidebar.text_input(
    "🔎 Search country",
    placeholder="Start typing, e.g. Ind..."
)

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
    incomes = sorted(filtered[income_col].dropna().astype(str).unique())
    selected_incomes = st.sidebar.multiselect(
        "Income group", incomes, default=incomes
    )
    filtered = filtered[
        filtered[income_col].astype(str).isin(selected_incomes)
    ]

if search:
    filtered = filtered[
        filtered["Country"].str.contains(
            search, case=False, na=False, regex=False
        )
    ]

if filtered.empty:
    st.warning("No countries match your search and filters.")
    st.stop()

suggestions = sorted(filtered["Country"].unique())

if st.session_state.selected_country not in suggestions:
    st.session_state.selected_country = suggestions[0]

# Visible matching suggestions update as the user types.
selected_country = st.sidebar.selectbox(
    "Country suggestions",
    suggestions,
    index=suggestions.index(st.session_state.selected_country),
    key="country_suggestion"
)
st.session_state.selected_country = selected_country

st.sidebar.divider()
st.sidebar.markdown("### 🎨 Completeness colours")
for band, colour in COLORS.items():
    if band != "Unknown":
        st.sidebar.markdown(
            f'<span style="color:{colour};font-size:20px">●</span> {band}',
            unsafe_allow_html=True
        )
st.sidebar.caption("DCS measures availability, not accuracy.")

# ---------------- HEADER AND METRICS ----------------
st.title("🌐 World Data Completeness Dashboard")
st.write(
    "Explore World Bank indicator availability, compare economies, "
    "and identify missing development data."
)
st.caption("World Bank indicators · 2015–2024")

global_mean = countries["DCS (%)"].mean()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Economies", len(countries))
m2.metric("Global average DCS", f"{global_mean:.1f}%")
m3.metric(
    "100% complete",
    int((countries["DCS (%)"] == 100).sum())
)
m4.metric(
    "With missing data",
    int((countries["DCS (%)"] < 100).sum())
)

st.divider()

# =========================================================
# 1. WORLD MAP
# =========================================================
st.header("🗺️ World data completeness map")
st.caption(
    "Hover for country details. Click a country to open its profile."
)

map_data = filtered.copy()

if st.session_state.coverage_band != "All countries":
    map_data = map_data[
        map_data["Completeness Band"] == st.session_state.coverage_band
    ]

if map_data.empty:
    st.warning("No countries match the current map filters.")
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
            [0.0, "#E63946"],
            [0.3, "#F6B5D2"],
            [0.6, "#FF9F43"],
            [0.8, "#9B5DE5"],
            [1.0, "#4263EB"]
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
            marker_line_color="white",
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
# 2. PIE CHART WITH ALWAYS-VISIBLE COUNTRY FILTER
# =========================================================
st.divider()
st.header("🍩 Countries by completeness group")
st.write(
    "Click a pie slice to select a score group. "
    "You can also choose the group from the selector beside the chart."
)

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
    hole=0.45,
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
    height=420,
    margin=dict(l=10, r=10, t=20, b=10),
    showlegend=False
)

pie_col, country_list_col = st.columns([1, 1.2])

with pie_col:
    pie_event = st.plotly_chart(
        pie,
        use_container_width=True,
        key="coverage_pie",
        on_select="rerun",
        selection_mode="points"
    )

# A pie click schedules the band update for the next run.
# The selector below is the reliable fallback if chart selection
# isn't supported by the browser or Streamlit version.
if pie_event and pie_event.selection.points:
    point = pie_event.selection.points[0]
    clicked_band = point.get("label")

    if clicked_band not in BANDS:
        point_index = point.get(
            "point_index", point.get("point_number")
        )
        if point_index is not None and 0 <= point_index < len(band_counts):
            clicked_band = band_counts.iloc[point_index]["Completeness Band"]

    if clicked_band in BANDS:
        if clicked_band != st.session_state.coverage_band:
            st.session_state["pending_band"] = clicked_band
            st.rerun()

with country_list_col:
    st.subheader("🔎 Filter and view countries")

    band_options = ["All countries"] + BANDS
    current_band = st.session_state.coverage_band
    if current_band not in band_options:
        current_band = "All countries"

    chosen_band = st.selectbox(
        "Choose a completeness group",
        band_options,
        index=band_options.index(current_band),
        key="band_selector"
    )

    # Update the selected group without modifying the widget's own key.
    if chosen_band != st.session_state.coverage_band:
        st.session_state.coverage_band = chosen_band
        st.rerun()

    if chosen_band == "All countries":
        st.info("Select a score group to see its matching countries.")
    else:
        group = countries[
            countries["Completeness Band"] == chosen_band
        ].sort_values(
            ["DCS (%)", "Country"],
            ascending=[True, True]
        )

        st.markdown(f"**{chosen_band}**")
        st.caption(f"{len(group)} countries in this group")

        if group.empty:
            st.info("There are no countries in this group.")
        else:
            # Display the actual filtered country list, not just a selector.
            st.dataframe(
                group[["Country", "DCS (%)", "Country Code"]].rename(
                    columns={"DCS (%)": "DCS (%)"}
                ),
                use_container_width=True,
                hide_index=True,
                height=280
            )

            country_names = group["Country"].tolist()
            country_to_open = st.selectbox(
                "Open a country profile",
                country_names,
                key=f"country_in_group_{chosen_band}"
            )

            if st.button(
                "Open selected country",
                key="open_group_country",
                use_container_width=True
            ):
                st.session_state["pending_country"] = country_to_open
                st.rerun()

    if st.button(
        "Clear group filter",
        key="clear_group_filter",
        use_container_width=True
    ):
        st.session_state["pending_band"] = "All countries"
        st.rerun()

# =========================================================
# 3. SELECTED COUNTRY PROFILE
# =========================================================
st.divider()

profile_rows = countries[
    countries["Country"] == st.session_state.selected_country
]
if profile_rows.empty:
    st.warning("Selected country is not available.")
    st.stop()

country = profile_rows.iloc[0]
code = country["Country Code"]

st.header(f"📍 {country['Country']} — Country Profile")

region = country.get(region_col, "Not available") if region_col else "Not available"
income = country.get(income_col, "Not available") if income_col else "Not available"
st.caption(f"Region: {region} · Income group: {income}")

p1, p2, p3, p4 = st.columns(4)
p1.metric("Overall DCS", f"{country['DCS (%)']:.1f}%")

recent = country.get("Recent DCS (%)", float("nan"))
p2.metric(
    "Recent DCS",
    f"{recent:.1f}%" if pd.notna(recent) else "N/A"
)

available_values = country.get("Available_Values", float("nan"))
missing_values = country.get("Missing_Values", float("nan"))

p3.metric(
    "Available values",
    int(available_values) if pd.notna(available_values) else "N/A"
)
p4.metric(
    "Missing values",
    int(missing_values) if pd.notna(missing_values) else "N/A"
)

# =========================================================
# 4. YEAR-WISE LINE GRAPH
# =========================================================
st.divider()
st.header("📈 Year-wise completeness trend")
st.caption(
    "The line shows how the selected country's data completeness "
    "changes from year to year."
)

country_yearly = yearly[yearly["Country Code"] == code].copy()

if not country_yearly.empty and {"Year", "DCS (%)"}.issubset(country_yearly.columns):
    country_yearly = country_yearly.dropna(
        subset=["Year", "DCS (%)"]
    ).sort_values("Year")

    line = px.line(
        country_yearly,
        x="Year",
        y="DCS (%)",
        markers=True,
        title=f"Annual DCS — {country['Country']}",
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
        height=400,
        yaxis=dict(range=[0, 105], ticksuffix="%"),
        xaxis_title="Year",
        yaxis_title="Data Completeness Score (%)"
    )
    st.plotly_chart(
        line,
        use_container_width=True,
        key="yearly_trend"
    )

    trend = country_yearly.sort_values("Year")
    if len(trend) >= 2:
        change = (
            trend["DCS (%)"].iloc[-1] - trend["DCS (%)"].iloc[0]
        )
        st.metric(
            f"Change from {int(trend['Year'].iloc[0])} "
            f"to {int(trend['Year'].iloc[-1])}",
            f"{change:+.1f} percentage points"
        )
else:
    st.info("Yearly scores are unavailable for this country.")

# =========================================================
# 5. INDICATOR AVAILABILITY
# =========================================================
st.divider()
st.header("🧩 Indicator availability")
st.caption(
    "Compare how completely each of the seven indicators is reported "
    "for the selected country."
)

country_indicators = indicators[
    indicators["Country Code"] == code
].copy()

if (
    indicator_col
    and not country_indicators.empty
    and "Year" in country_indicators.columns
):
    if available_col:
        country_indicators["_available"] = (
            country_indicators[available_col]
            .astype(str).str.lower()
            .isin(["true", "1", "yes"])
        )
    elif "Value" in country_indicators.columns:
        country_indicators["_available"] = (
            country_indicators["Value"].notna()
        )
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
    summary["Missing_Years"] = (
        summary["Total_Years"] - summary["Available_Years"]
    )
    summary["Completeness (%)"] = (
        summary["Available_Years"]
        / summary["Total_Years"].replace(0, pd.NA)
        * 100
    )

    bar = px.bar(
        summary.sort_values("Completeness (%)"),
        x="Completeness (%)",
        y=indicator_col,
        orientation="h",
        color="Completeness (%)",
        color_continuous_scale=[
            "#E63946", "#FF9F43", "#9B5DE5", "#4263EB"
        ],
        range_color=(0, 100),
        hover_data=[
            "Available_Years", "Missing_Years", "Total_Years"
        ]
    )
    bar.update_layout(
        paper_bgcolor="#10131F",
        plot_bgcolor="#191D2D",
        font_color="#F5F5FA",
        height=420,
        xaxis=dict(range=[0, 100], ticksuffix="%"),
        yaxis_title="",
        coloraxis_showscale=False
    )
    st.plotly_chart(
        bar,
        use_container_width=True,
        key="indicator_chart"
    )

    with st.expander("View indicator summary and missing years"):
        st.dataframe(
            summary.rename(columns={indicator_col: "Indicator"}),
            use_container_width=True,
            hide_index=True
        )

    # Show individual indicator records when useful columns exist.
    with st.expander("View yearly indicator records"):
        display_cols = [
            c for c in [
                "Year", indicator_col, "Value",
                "Available", "Is Available", "A
