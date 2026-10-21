import re
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events

# =========================================================
# PAGE SETUP
# =========================================================
st.set_page_config(
    page_title="World Data Completeness",
    page_icon="🌍",
    layout="wide"
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #10131F;
        color: #F5F5FA;
    }
    [data-testid="stSidebar"] {
        background-color: #191D2D;
    }
    div[data-testid="stMetric"] {
        background-color: #191D2D;
        border: 1px solid #30364A;
        padding: 14px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🌍 World Data Completeness Dashboard")
st.caption(
    "Explore the availability of World Bank indicators "
    "across countries and years."
)

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data
def load_data():
    countries = pd.read_csv("dashboard_data.csv")
    yearly = pd.read_csv("yearly_scores.csv")
    indicators = pd.read_csv("indicator_availability.csv")
    return countries, yearly, indicators


try:
    country_df, yearly_df, indicator_df = load_data()
except Exception as exc:
    st.error(
        "Could not load the CSV files. Ensure all three files "
        "are in the same GitHub repository as app.py."
    )
    st.code(str(exc))
    st.stop()


# =========================================================
# COLUMN DETECTION
# =========================================================
def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_col(df, candidates):
    available = {normalize(c): c for c in df.columns}
    for candidate in candidates:
        if normalize(candidate) in available:
            return available[normalize(candidate)]
    return None


country_col = find_col(
    country_df, ["Country", "Country Name", "Economy"]
)
code_col = find_col(
    country_df, ["Country Code", "CountryCode", "ISO3", "ISO Code"]
)
year_col = find_col(country_df, ["Year", "Time"])
dcs_col = find_col(
    country_df,
    ["DCS (%)", "DCS", "Completeness Score", "Data Completeness Score"]
)

global_year_col = find_col(yearly_df, ["Year", "Time"])
global_avg_col = find_col(
    yearly_df, ["Average_DCS", "Average DCS", "Mean DCS", "Average Completeness"]
)
global_median_col = find_col(
    yearly_df, ["Median_DCS", "Median DCS", "Median Completeness"]
)

indicator_name_col = find_col(
    indicator_df, ["Indicator", "Indicator Name", "Series Name"]
)
indicator_pct_col = find_col(
    indicator_df,
    ["Availability (%)", "Availability", "Availability Percentage",
     "Completeness (%)", "DCS (%)"]
)
indicator_available_col = find_col(
    indicator_df,
    ["Available Records", "Available", "Available Values",
     "Non Missing Values", "Non-Missing Values"]
)
indicator_total_col = find_col(
    indicator_df,
    ["Total Records", "Total", "Expected Records", "Expected Values"]
)

if country_col is None or dcs_col is None:
    st.error(
        "dashboard_data.csv must contain a country column and a "
        "completeness score column."
    )
    st.write("Columns found:", list(country_df.columns))
    st.stop()

for df, cols in [
    (country_df, [year_col, dcs_col]),
    (yearly_df, [global_year_col, global_avg_col, global_median_col]),
    (indicator_df, [
        indicator_pct_col, indicator_available_col, indicator_total_col
    ])
]:
    for col in cols:
        if col is not None:
            df[col] = pd.to_numeric(df[col], errors="coerce")

country_df = country_df.dropna(subset=[country_col]).copy()
country_df[country_col] = country_df[country_col].astype(str).str.strip()
country_df = country_df.dropna(subset=[dcs_col]).copy()

if country_df.empty:
    st.error("No usable country completeness scores were found.")
    st.stop()

# Calculate indicator availability if only counts are available.
if (
    indicator_pct_col is None
    and indicator_available_col is not None
    and indicator_total_col is not None
):
    indicator_df["Calculated Availability (%)"] = (
        indicator_df[indicator_available_col]
        / indicator_df[indicator_total_col].replace(0, pd.NA)
        * 100
    )
    indicator_pct_col = "Calculated Availability (%)"


# =========================================================
# MAP DATA: ONE SCORE PER COUNTRY
# =========================================================
if year_col is not None and country_df[year_col].notna().any():
    latest_year = country_df[year_col].max()
    map_df = country_df[country_df[year_col] == latest_year].copy()
else:
    latest_year = None
    map_df = country_df.copy()

map_df = map_df.drop_duplicates(subset=[country_col], keep="last")
map_df = map_df.dropna(subset=[dcs_col]).copy()

if map_df.empty:
    st.error("No country scores are available for the map.")
    st.stop()

country_names = sorted(map_df[country_col].unique().tolist())

# =========================================================
# SCORE GROUPS
# =========================================================
def score_group(score):
    if pd.isna(score):
        return "Unknown"
    if score >= 90:
        return "90–100% (Very high)"
    if score >= 75:
        return "75–89.9% (High)"
    if score >= 50:
        return "50–74.9% (Moderate)"
    return "Below 50% (Low)"


band_order = [
    "90–100% (Very high)",
    "75–89.9% (High)",
    "50–74.9% (Moderate)",
    "Below 50% (Low)"
]

map_df["Score Group"] = map_df[dcs_col].apply(score_group)

band_counts = (
    map_df["Score Group"]
    .value_counts()
    .reindex(band_order, fill_value=0)
    .rename_axis("Score Group")
    .reset_index(name="Countries")
)

band_colors = {
    "90–100% (Very high)": "#2ECC71",
    "75–89.9% (High)": "#3498DB",
    "50–74.9% (Moderate)": "#F1C40F",
    "Below 50% (Low)": "#E84393"
}


# =========================================================
# INTERACTION STATE
# =========================================================
if "selected_country" not in st.session_state:
    st.session_state["selected_country"] = country_names[0]

if st.session_state["selected_country"] not in country_names:
    st.session_state["selected_country"] = country_names[0]

if "selected_band" not in st.session_state:
    st.session_state["selected_band"] = "All countries"


# =========================================================
# SIDEBAR: SEARCHABLE COUNTRY SUGGESTIONS
# =========================================================
st.sidebar.title("Dashboard Controls")

search_text = st.sidebar.text_input(
    "Search for a country",
    placeholder="Type a country name..."
)

if search_text.strip():
    suggestions = [
        name for name in country_names
        if search_text.lower() in name.lower()
    ]
else:
    suggestions = country_names

if not suggestions:
    st.sidebar.warning("No matching countries found.")
    suggestions = country_names

current_country = st.session_state["selected_country"]
if current_country not in suggestions:
    current_country = suggestions[0]

suggested_country = st.sidebar.selectbox(
    "Country suggestions",
    options=suggestions,
    index=suggestions.index(current_country)
)

if suggested_country != st.session_state["selected_country"]:
    st.session_state["selected_country"] = suggested_country


# =========================================================
# KPI CARDS
# =========================================================
st.subheader("Global Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Countries / Economies", f"{map_df[country_col].nunique():,}")
c2.metric("Average Completeness", f"{map_df[dcs_col].mean():.2f}%")
c3.metric("Median Completeness", f"{map_df[dcs_col].median():.2f}%")
c4.metric("Countries at 100%", f"{int((map_df[dcs_col] >= 100).sum()):,}")


# =========================================================
# 1. WORLD MAP — CLICK A COUNTRY TO OPEN ITS PROFILE
# =========================================================
st.divider()
st.subheader("🗺️ World Data Completeness Map")

map_location_col = code_col if code_col is not None else country_col

map_fig = px.choropleth(
    map_df,
    locations=map_location_col,
    locationmode="ISO-3" if code_col is not None else "country names",
    color=dcs_col,
    hover_name=country_col,
    hover_data={
        dcs_col: ":.2f",
        "Score Group": True
    },
    color_continuous_scale=[
        "#C0395A", "#E67E22", "#F1C40F", "#2ECC71", "#2471A3"
    ],
    range_color=(0, 100),
    labels={dcs_col: "Completeness (%)"}
)

map_fig.update_layout(
    paper_bgcolor="#10131F",
    geo=dict(
        bgcolor="#10131F",
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#586174",
        showocean=True,
        oceancolor="#151B2B",
        showland=True,
        landcolor="#242B3D"
    ),
    font=dict(color="#F5F5FA"),
    margin=dict(l=0, r=0, t=30, b=0)
)

map_clicks = plotly_events(
    map_fig,
    click_event=True,
    select_event=False,
    hover_event=False,
    override_height=520,
    override_width="100%",
    key="world_map_clicks"
)

if map_clicks:
    clicked = map_clicks[-1]

    # Choropleth click events commonly return the location code.
    clicked_location = clicked.get("location")

    # Some component/browser combinations return the point index.
    if clicked_location is None:
        point_index = clicked.get("pointNumber")
        if point_index is not None:
            point_index = int(point_index)
            if 0 <= point_index < len(map_df):
                clicked_location = map_df.iloc[point_index][map_location_col]

    if clicked_location is not None:
        match = map_df[
            map_df[map_location_col].astype(str)
            == str(clicked_location)
        ]

        if match.empty:
            match = map_df[
                map_df[country_col].astype(str)
                == str(clicked_location)
            ]

        if not match.empty:
            clicked_country = match.iloc[0][country_col]
            if clicked_country != st.session_state["selected_country"]:
                st.session_state["selected_country"] = clicked_country
                st.rerun()

if latest_year is not None:
    st.caption(f"Map displays the latest available year: {int(latest_year)}.")


# =========================================================
# 2. PIE CHART — CLICK A SLICE TO FILTER THE COUNTRY LIST
# =========================================================
st.divider()
st.subheader("🥧 Country Distribution by Completeness")

pie_col, list_col = st.columns([1, 1])

with pie_col:
    pie_fig = px.pie(
        band_counts,
        names="Score Group",
        values="Countries",
        hole=0.35,
        color="Score Group",
        color_discrete_map=band_colors,
        title="Click a slice to see its countries"
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
        plot_bgcolor="#10131F",
        font=dict(color="#F5F5FA"),
        margin=dict(l=10, r=10, t=55, b=10),
        showlegend=True
    )

    pie_clicks = plotly_events(
        pie_fig,
        click_event=True,
        select_event=False,
        hover_event=False,
        override_height=430,
        override_width="100%",
        key="score_pie_clicks"
    )

    if pie_clicks:
        clicked_pie = pie_clicks[-1]
        pie_index = clicked_pie.get("pointNumber")

        if pie_index is not None:
            pie_index = int(pie_index)
            if 0 <= pie_index < len(band_order):
                st.session_state["selected_band"] = band_order[pie_index]
                st.rerun()

with list_col:
    st.markdown("#### Countries in this completeness group")

    selected_band = st.selectbox(
        "Score group",
        options=["All countries"] + band_order,
        index=(
            ["All countries"] + band_order
        ).index(st.session_state["selected_band"])
    )

    if selected_band != st.session_state["selected_band"]:
        st.session_state["selected_band"] = selected_band
        st.rerun()

    if selected_band == "All countries":
        list_df = map_df.copy()
    else:
        list_df = map_df[
            map_df["Score Group"] == selected_band
        ].copy()

    list_df = list_df.sort_values(dcs_col, ascending=False)

    st.caption(f"{len(list_df)} countries in this group.")

    display_cols = [country_col, dcs_col, "Score Group"]
    if code_col is not None:
        display_cols.insert(1, code_col)

    st.dataframe(
        list_df[display_cols].rename(
            columns={
                country_col: "Country",
                dcs_col: "Completeness (%)"
            }
        ),
        use_container_width=True,
        hide_index=True,
        height=350
    )

    if not list_df.empty:
        profile_choice = st.selectbox(
            "Choose a country from this list",
            options=list_df[country_col].tolist()
        )

        if st.button("Show this country's details", use_container_width=True):
            st.session_state["selected_country"] = profile_choice
            st.rerun()


# =========================================================
# 3. SELECTED COUNTRY DETAILS + YEARLY LINE GRAPH
# =========================================================
st.divider()

selected_country = st.session_state["selected_country"]
st.subheader(f"📈 Country Details: {selected_country}")

profile_df = country_df[
    country_df[country_col] == selected_country
].copy()

if year_col is not None:
    profile_df = profile_df.sort_values(year_col)

if not profile_df.empty:
    latest_profile_score = profile_df[dcs_col].iloc[-1]
    st.metric("Latest available completeness score", f"{latest_profile_score:.2f}%")

    if year_col is not None and profile_df[year_col].nunique() >= 2:
        profile_fig = px.line(
            profile_df,
            x=year_col,
            y=dcs_col,
            markers=True,
            title=f"Yearly Completeness Trend — {selected_country}",
            labels={
                year_col: "Year",
                dcs_col: "Completeness (%)"
            }
        )

        profile_fig.update_traces(
            line=dict(color="#3498DB", width=3),
            marker=dict(size=8)
        )
        profile_fig.update_yaxes(range=[0, 100])
        profile_fig.update_layout(
            paper_bgcolor="#10131F",
            plot_bgcolor="#10131F",
            font=dict(color="#F5F5FA"),
            margin=dict(l=20, r=20, t=55, b=20)
        )

        st.plotly_chart(profile_fig, use_container_width=True)

        first_score = profile_df[dcs_col].iloc[0]
        last_score = profile_df[dcs_col].iloc[-1]
        difference = last_score - first_score

        st.metric(
            "Change from first to latest available year",
            f"{difference:+.2f} percentage points"
        )
    else:
        st.info(
            "A country-level line graph requires multiple years "
            "of completeness scores for this country."
        )

    with st.expander("View all records for this country"):
        st.dataframe(
            profile_df,
            use_container_width=True,
            hide_index=True
        )
else:
    st.warning("No detailed records were found for this country.")


# =========================================================
# 4. GLOBAL YEARLY TREND — REPLACES THE COMPARATOR
# =========================================================
st.divider()
st.subheader("📉 Global Completeness Trend (2015–2024)")

if global_year_col is not None and global_avg_col is not None:
    trend_df = yearly_df.dropna(
        subset=[global_year_col, global_avg_col]
    ).sort_values(global_year_col)

    global_fig = go.Figure()

    global_fig.add_trace(
        go.Scatter(
            x=trend_df[global_year_col],
            y=trend_df[global_avg_col],
            mode="lines+markers+text",
            name="Average completeness",
            text=[f"{v:.2f}%" for v in trend_df[global_avg_col]],
            textposition="top center",
            line=dict(color="#3498DB", width=3),
            marker=dict(size=8)
        )
    )

    if global_median_col is not None:
        median_df = trend_df.dropna(subset=[global_median_col])
        global_fig.add_trace(
            go.Scatter(
                x=median_df[global_year_col],
                y=median_df[global_median_col],
                mode="lines+markers",
                name="Median completeness",
                line=dict(color="#F1C40F", width=2, dash="dash")
            )
        )

    global_fig.update_layout(
        title="Average and Median Completeness by Year",
        xaxis_title="Year",
        yaxis_title="Completeness (%)",
        paper_bgcolor="#10131F",
        plot_bgcolor="#10131F",
        font=dict(color="#F5F5FA"),
        margin=dict(l=20, r=20, t=55, b=20)
    )
    global_fig.update_yaxes(range=[0, 100])

    st.plotly_chart(global_fig, use_container_width=True)

    if len(trend_df) >= 2:
        first = trend_df.iloc[0]
        last = trend_df.iloc[-1]
        change = last[global_avg_col] - first[global_avg_col]

        if change > 0:
            st.success(
                f"Average completeness increased by {change:.2f} "
                f"percentage points between {int(first[global_year_col])} "
                f"and {int(last[global_year_col])}."
            )
        elif change < 0:
            st.warning(
                f"Average completeness decreased by {abs(change):.2f} "
                f"percentage points between {int(first[global_year_col])} "
                f"and {int(last[global_year_col])}."
            )
        else:
            st.info("Average completeness was unchanged between the first and last available years.")
else:
    st.error(
        "yearly_scores.csv needs a Year column and an Average_DCS "
        "or equivalent average-completeness column."
    )


# =========================================================
# 5. INDICATOR AVAILABILITY BAR CHART
# =========================================================
st.divider()
st.subheader("📊 Indicator Availability")

if indicator_name_col is not None:
    chart_df = indicator_df.copy()

    if indicator_pct_col is not None:
        chart_df = chart_df.dropna(subset=[indicator_pct_col])
        chart_df = chart_df.sort_values(indicator_pct_col)

        indicator_fig = px.bar(
            chart_df,
            x=indicator_pct_col,
            y=indicator_name_col,
            orientation="h",
            text=indicator_pct_col,
            title="Availability by Indicator",
            labels={
                indicator_pct_col: "Availability (%)",
                indicator_name_col: "Indicator"
            }
        )
        indicator_fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
            cliponaxis=False
        )
        indicator_fig.update_xaxes(range=[0, 110])

    elif indicator_available_col is not None:
        chart_df = chart_df.dropna(subset=[indicator_available_col])
        chart_df = chart_df.sort_values(indicator_available_col)

        indicator_fig = px.bar(
            chart_df,
            x=indicator_available_col,
            y=indicator_name_col,
            orientation="h",
            text=indicator_available_col,
            title="Available Records by Indicator",
            labels={
                indicator_available_col: "Available records",
                indicator_name_col: "Indicator"
            }
        )
        indicator_fig.update_traces(textposition="outside"
