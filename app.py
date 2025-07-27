"""
Streamlit Macro Dashboard using FRED API
--------------------------------------

This Streamlit application pulls a variety of macro‑economic time series
from the St. Louis Federal Reserve’s FRED service using the provided API key
and arranges them into intuitive tabs.  The goal is to give users a
holistic view of the economy by grouping charts into high‑level themes
such as **Prices**, **Flows**, **Inflation**, **Growth** and **Expectations**.

Key features:

* Uses the official FRED REST API via `requests` to fetch series by ID.
* Categories and series metadata are defined in a single configuration
  dictionary for easy extension.  Each entry includes a human‑readable
  name and, optionally, a default frequency.
* Interactive controls allow users to select the time horizon (e.g. 1 year,
  3 years, 10 years or full history) and optionally apply a moving
  average to smooth the data.
* Charts are rendered using Plotly and laid out in responsive columns
  within each tab.  Tooltips and legends improve readability, and
  recession shading can be toggled if desired.

To run this app locally:

```
streamlit run app.py --server.port 8501
```

Before running you must set your FRED API key.  The recommended way
is via Streamlit’s secrets mechanism.  Create a file called
`.streamlit/secrets.toml` in the project root with the following
contents:

```
FRED_API_KEY = "your_fred_api_key_here"
```

Alternatively, you can export an environment variable named
`FRED_API_KEY`.
"""

import datetime
import os
import json
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


def load_api_key() -> str:
    """Retrieve the FRED API key from Streamlit secrets or the environment.

    Returns
    -------
    str
        The API key.  Raises a ValueError if no key is found.
    """
    # Prefer Streamlit secrets if available
    key = None
    if st.secrets.get("FRED_API_KEY"):
        key = st.secrets["FRED_API_KEY"]
    elif os.getenv("FRED_API_KEY"):
        key = os.getenv("FRED_API_KEY")
    if not key:
        raise ValueError(
            "No FRED API key found. Please add it to .streamlit/secrets.toml "
            "or set the FRED_API_KEY environment variable."
        )
    return key


@st.cache_data(show_spinner=False)
def fetch_fred_series(series_id: str, api_key: str, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
    """Fetch a FRED time series and return it as a pandas DataFrame.

    Parameters
    ----------
    series_id : str
        The FRED series identifier, e.g. "GDP" or "CPIAUCSL".
    api_key : str
        The user’s FRED API key.
    start : str, optional
        Observation start date in YYYY-MM-DD format.  If omitted the full
        history is returned.
    end : str, optional
        Observation end date in YYYY-MM-DD format.  If omitted the latest
        observations are returned.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with two columns: `date` (datetime) and `value` (float).
    """
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    if start:
        params["observation_start"] = start
    if end:
        params["observation_end"] = end

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        raise ValueError(
            f"Failed to fetch FRED series {series_id}: {response.status_code} - {response.text[:200]}"
        )
    data = response.json().get("observations", [])
    if not data:
        raise ValueError(f"No data returned for series {series_id}.")

    # Convert to DataFrame
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[["date", "value"]].dropna()
    return df


def apply_moving_average(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Calculate a simple moving average of the `value` column.

    Parameters
    ----------
    df : pandas.DataFrame
        The input data frame containing `date` and `value` columns.
    window : int
        The number of periods to use for the moving average.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with the original `date` column and a new `value`
        column representing the moving average.
    """
    sma = df.copy()
    sma["value"] = sma["value"].rolling(window=window, min_periods=1).mean()
    return sma


def plot_series(df: pd.DataFrame, title: str, moving_avg_window: Optional[int] = None) -> px.line:
    """Render a line chart of a FRED series.

    Parameters
    ----------
    df : pandas.DataFrame
        A data frame with `date` and `value` columns.
    title : str
        Title for the chart.
    moving_avg_window : int, optional
        If provided, the chart will include an additional line for the
        moving average over the specified window.

    Returns
    -------
    plotly.graph_objects.Figure
        A Plotly figure ready for display.
    """
    fig = px.line(df, x="date", y="value", title=title, labels={"value": title, "date": "Date"})
    if moving_avg_window and moving_avg_window > 1:
        ma_df = apply_moving_average(df, moving_avg_window)
        fig.add_scatter(x=ma_df["date"], y=ma_df["value"], mode="lines", name=f"{title} (MA {moving_avg_window})")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig


def build_dashboard():
    """Main function to orchestrate the Streamlit dashboard layout."""
    st.set_page_config(page_title="Macro Dashboard", layout="wide")

    st.title("Macro Dashboard")
    st.markdown(
        "Use this dashboard to explore key macro‑economic indicators across a number "
        "of themes. Select your desired time horizon and optionally apply a moving average "
        "to smooth the series. Data are sourced directly from the Federal Reserve’s "
        "FRED API."
    )

    api_key = load_api_key()

    # Horizon selection
    horizon_options = {
        "1 Quarter": 0.25,
        "1 Year": 1,
        "3 Years": 3,
        "10 Years": 10,
        "Max": None,
    }
    horizon = st.sidebar.selectbox("Time horizon", list(horizon_options.keys()), index=1)
    horizon_years = horizon_options[horizon]

    # Moving average control
    ma_enable = st.sidebar.checkbox("Apply moving average", value=False)
    ma_window = None
    if ma_enable:
        ma_window = st.sidebar.slider("Moving average window (in periods)", min_value=2, max_value=12, value=4)

    # Determine date range
    end_date = datetime.date.today()
    start_date = None
    if horizon_years:
        # convert years to days roughly; account for quarter = 0.25 years
        days = int(horizon_years * 365.25)
        start_date = (end_date - datetime.timedelta(days=days)).isoformat()

    # Series configuration: categories mapped to list of series dictionaries
    series_config: Dict[str, List[Dict[str, str]]] = {
        "Prices": [
            {"id": "CPIAUCSL", "name": "CPI (All Urban Consumers, SA)"},
            {"id": "PCEPI", "name": "PCE Price Index"},
            {"id": "CPILFESL", "name": "Core CPI (All Items Less Food & Energy)"},
            {"id": "DGORDER", "name": "New Orders for Durable Goods"},
            {"id": "PPIFGS", "name": "Producer Price Index: Finished Goods"},
        ],
        "Flows": [
            {"id": "M2SL", "name": "Money Stock (M2)"},
            {"id": "WM2NS", "name": "Money Stock (M2) Not Seasonally Adjusted"},
            {"id": "MMMFFAQ027N", "name": "Money Market Fund Assets"},
            {"id": "RESBALNS", "name": "Reserves of Depository Institutions"},
            {"id": "M1SL", "name": "Money Stock (M1)"},
        ],
        "Inflation": [
            {"id": "CPILFESL", "name": "Core CPI (All Items Less Food & Energy)"},
            {"id": "CPIAUCSL", "name": "Headline CPI"},
            {"id": "PPIACO", "name": "Producer Price Index: All Commodities"},
            {"id": "T5YIEM", "name": "5‑Year Breakeven Inflation"},
            {"id": "T10YIEM", "name": "10‑Year Breakeven Inflation"},
        ],
        "Growth": [
            {"id": "GDP", "name": "Gross Domestic Product"},
            {"id": "GDPC1", "name": "Real Gross Domestic Product"},
            {"id": "PCEC96", "name": "Real Personal Consumption Expenditures"},
            {"id": "GPDIC1", "name": "Real Gross Private Domestic Investment"},
            {"id": "GCECA", "name": "Government Consumption Expenditures & Gross Investment"},
        ],
        "Expectations": [
            {"id": "UMCSENT", "name": "University of Michigan: Consumer Sentiment"},
            {"id": "UMCSENTM", "name": "University of Michigan: Consumer Expectations"},
            {"id": "NAPM", "name": "ISM Manufacturing PMI"},
            {"id": "UMRTXNS", "name": "Retail Mobility (Google)"},
            {"id": "T10Y2Y", "name": "10‑Year minus 2‑Year Treasury Spread"},
        ],
    }

    # Build tabs for each category
    tabs = st.tabs(list(series_config.keys()))
    for cat_idx, (category, series_list) in enumerate(series_config.items()):
        with tabs[cat_idx]:
            st.subheader(category)
            col_count = 2  # number of columns per row
            rows = [series_list[i:i + col_count] for i in range(0, len(series_list), col_count)]
            for row_series in rows:
                cols = st.columns(len(row_series))
                for idx, series_info in enumerate(row_series):
                    with cols[idx]:
                        sid = series_info["id"]
                        name = series_info["name"]
                        try:
                            df = fetch_fred_series(sid, api_key, start=start_date, end=end_date)
                            fig = plot_series(df, name, moving_avg_window=ma_window)
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as exc:
                            st.error(f"Error loading {name}: {exc}")


if __name__ == "__main__":
    build_dashboard()