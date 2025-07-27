import datetime
import os
from typing import Dict, List, Optional
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

def load_api_key() -> str:
    if st.secrets.get("FRED_API_KEY"):
        return st.secrets["FRED_API_KEY"]
    elif os.getenv("FRED_API_KEY"):
        return os.getenv("FRED_API_KEY")
    else:
        raise ValueError("FRED API key not found.")

@st.cache_data(show_spinner=False)
def fetch_fred_series(series_id: str, api_key: str, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
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
        raise ValueError(f"Failed to fetch FRED series {series_id}: {response.status_code} - {response.text[:200]}")
    data = response.json().get("observations", [])
    if not data:
        raise ValueError(f"No data returned for series {series_id}.")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["date", "value"]].dropna()

def apply_moving_average(df: pd.DataFrame, window: int) -> pd.DataFrame:
    sma = df.copy()
    sma["value"] = sma["value"].rolling(window=window, min_periods=1).mean()
    return sma

def plot_series(df: pd.DataFrame, title: str, moving_avg_window: Optional[int] = None) -> px.line:
    fig = px.line(df, x="date", y="value", title=title, labels={"value": title, "date": "Date"})
    if moving_avg_window and moving_avg_window > 1:
        ma_df = apply_moving_average(df, moving_avg_window)
        fig.add_scatter(x=ma_df["date"], y=ma_df["value"], mode="lines", name=f"{title} (MA {moving_avg_window})")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig

def build_dashboard():
    st.set_page_config(page_title="Macro Dashboard", layout="wide")

    api_key = load_api_key()

    series_config: Dict[str, List[Dict[str, str]]] = {
        "Prices": [
            {"id": "CPIAUCSL", "name": "CPI (All Urban Consumers, SA)"},
            {"id": "PCEPI", "name": "PCE Price Index"},
            {"id": "CPILFESL", "name": "Core CPI (Less Food & Energy)"},
            {"id": "DGORDER", "name": "New Orders for Durable Goods"},
            {"id": "WPUFD4", "name": "PPI: Finished Goods"},
        ],
        "Flows": [
            {"id": "M2SL", "name": "Money Stock (M2)"},
            {"id": "WM2NS", "name": "Money Stock (M2) NSA"},
            {"id": "WMMFSL", "name": "Money Market Fund Assets (Weekly)"},
            {"id": "WRESBAL", "name": "Reserves of Depository Institutions (Weekly)"},
            {"id": "M1SL", "name": "Money Stock (M1)"},
        ],
        "Inflation": [
            {"id": "CPILFESL", "name": "Core CPI (Less Food & Energy)"},
            {"id": "CPIAUCSL", "name": "Headline CPI"},
            {"id": "PPIACO", "name": "Producer Price Index: All Commodities"},
            {"id": "T5YIEM", "name": "5‑Year Breakeven Inflation"},
            {"id": "T10YIEM", "name": "10‑Year Breakeven Inflation"},
        ],
        "Growth": [
            {"id": "GDP", "name": "Gross Domestic Product"},
            {"id": "GDPC1", "name": "Real GDP"},
            {"id": "PCEC96", "name": "Real Personal Consumption Expenditures"},
            {"id": "GPDIC1", "name": "Real Private Domestic Investment"},
            {"id": "GCECA", "name": "Gov’t Consumption & Investment"},
        ],
        "Expectations": [
            {"id": "UMCSENT", "name": "UMich: Consumer Sentiment"},
            {"id": "NAPMPI", "name": "ISM Manufacturing PMI (Revised)"},
            {"id": "T10Y2Y", "name": "10Y - 2Y Treasury Spread"},
        ],
    }

    tabs = st.tabs(list(series_config.keys()))
    for cat_idx, (category, series_list) in enumerate(series_config.items()):
        with tabs[cat_idx]:
            st.subheader(category)
            col_count = 2
            rows = [series_list[i:i + col_count] for i in range(0, len(series_list), col_count)]
            for row_series in rows:
                cols = st.columns(len(row_series))
                for idx, series_info in enumerate(row_series):
                    with cols[idx]:
                        sid = series_info["id"]
                        name = series_info["name"]
                        try:
                            df = fetch_fred_series(sid, api_key)
                            fig = plot_series(df, name)
                            st.plotly_chart(fig, use_container_width=True, key=f"{sid}_chart")
                        except Exception as exc:
                            st.error(f"Error loading {name}: {exc}")

if __name__ == "__main__":
    build_dashboard()
