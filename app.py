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

    # ✅ Debug: Confirm dashboard is running
    st.write("✅ build_dashboard is running")

    # 📊 Dummy chart for sanity check
    dummy_data = pd.DataFrame({
        "date": pd.date_range(end=datetime.date.today(), periods=30),
        "value": [i + (i % 5) for i in range(30)]
    }).set_index("date")
    st.line_chart(dummy_data)

    # 🚨 Commented out until debugging is done
    # api_key = load_api_key()
    # (your real dashboard logic continues here)

if __name__ == "__main__":
    build_dashboard()
