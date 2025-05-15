
import streamlit as st
import pandas as pd
import plotly.express as px
from fredapi import Fred
from datetime import datetime

st.set_page_config(layout="wide")

macro_info = {
    "Real GDP (Annual %)": "Measures inflation-adjusted output of the economy. A rising trend indicates healthy growth, while contraction may signal recession.",
    "Retail Sales YoY (%)": "Tracks consumer spending trends. Calculated as trailing 12-month % change.",
    "Industrial Production Index": "Shows the output of factories, mines, and utilities. YoY % change gives real growth.",
    "Construction Spending": "Captures private and public construction activity. We use 12-month % change to remove seasonality.",
    "Unemployment Rate (%)": "Percentage of people actively seeking jobs. This is a direct rate.",
    "Job Openings (JOLTS, M)": "The number of unfilled jobs. No transformation applied.",
    "Initial Jobless Claims (000s)": "Weekly gauge of layoffs. Plotted raw.",
    "Labor Force Participation Rate (%)": "Raw labor force engagement rate.",
    "CPI YoY (%)": "Consumer Price Index — % change over last 12 months.",
    "Core PCE YoY (%)": "Inflation metric favored by the Fed. We compute YoY % change.",
    "Avg Hourly Earnings YoY (%)": "Wage growth. Shown as YoY % change.",
    "Owner Equivalent Rent (CPI Proxy)": "Raw housing index. Displayed with YoY % transformation.",
    "Fed Funds Rate (%)": "Central bank policy rate. Plotted raw.",
    "Fed Balance Sheet ($T)": "Displayed in raw size. No transformation.",
    "SOFR (%)": "Short-term benchmark rate. Plotted raw.",
    "RRP Facility Usage ($B)": "Liquidity measure. Plotted raw.",
    "10Y Treasury Yield (%)": "Market bond yield. Plotted raw.",
    "2Y Treasury Yield (%)": "Plotted raw.",
    "2s10s Spread (%)": "Difference between 10Y and 2Y yield. Raw.",
    "AAA Corporate Bond Yield (%)": "Plotted raw.",
    "LEI YoY (%)": "Leading Economic Index. Raw %.",
    "Consumer Confidence (U Mich)": "Sentiment index. Raw."
}

fred = Fred(api_key="0aeeefb16f1283902cdfc629d5c4b39b")

# Series requiring YoY % transformation
yoy_transform_series = {
    "Retail Sales YoY (%)",
    "Industrial Production Index",
    "Construction Spending",
    "CPI YoY (%)",
    "Core PCE YoY (%)",
    "Avg Hourly Earnings YoY (%)",
    "Owner Equivalent Rent (CPI Proxy)"
}

sections = {
    "📈 Growth & Activity": {
        "Real GDP (Annual %)": "A191RL1Q225SBEA",
        "Retail Sales YoY (%)": "RSAFS",
        "Industrial Production Index": "INDPRO",
        "Construction Spending": "TTLCONS"
    },
    "👷 Labor Market": {
        "Unemployment Rate (%)": "UNRATE",
        "Job Openings (JOLTS, M)": "JTSJOL",
        "Initial Jobless Claims (000s)": "ICSA",
        "Labor Force Participation Rate (%)": "CIVPART"
    },
    "💸 Inflation & Prices": {
        "CPI YoY (%)": "CPIAUCSL",
        "Core PCE YoY (%)": "PCEPILFE",
        "Avg Hourly Earnings YoY (%)": "CES0500000003",
        "Owner Equivalent Rent (CPI Proxy)": "CUSR0000SEHC"
    },
    "🏦 Monetary Policy": {
        "Fed Funds Rate (%)": "FEDFUNDS",
        "Fed Balance Sheet ($T)": "WALCL",
        "SOFR (%)": "SOFR",
        "RRP Facility Usage ($B)": "RRPONTSYD"
    },
    "📉 Market Rates": {
        "10Y Treasury Yield (%)": "GS10",
        "2Y Treasury Yield (%)": "GS2",
        "2s10s Spread (%)": "T10Y2Y",
        "AAA Corporate Bond Yield (%)": "DAAA"
    },
    "📊 Business Sentiment": {
        "LEI YoY (%)": "USSLIND",
        "Consumer Confidence (U Mich)": "UMCSENT"
    }
}

def plot_series(series, label, apply_yoy):
    df = series.reset_index()
    df.columns = ['Date', 'Value']
    if apply_yoy:
        df['Value'] = df['Value'].pct_change(periods=12) * 100
        df = df.dropna()
    fig = px.line(df, x='Date', y='Value', title=label)
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x unified",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=3, label="3Y", step="year", stepmode="backward"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    return fig

st.title("📊 U.S. Macro Dashboard — Real-Time + Correct YoY %")

for section, indicators in sections.items():
    st.header(section)
    cols = st.columns(4)
    for i, (label, fred_id) in enumerate(indicators.items()):
        with cols[i % 4]:
            try:
                series = fred.get_series(fred_id, start_date="2005-01-01")
                if series is None or series.empty:
                    raise ValueError("No data returned")
                apply_yoy = label in yoy_transform_series
                fig = plot_series(series, label, apply_yoy)
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("ℹ️ Info"):
                    st.markdown(macro_info.get(label, "No info available for this chart."))
            except Exception as e:
                st.error(f"Error loading {label}: {e}")
