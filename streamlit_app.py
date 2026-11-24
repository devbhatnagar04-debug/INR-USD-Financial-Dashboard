import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date

st.set_page_config(page_title="INR–USD IFM Dashboard", page_icon="₹", layout="wide")
st.title("🇮🇳 INR–USD | International Financial Management Dashboard")
st.caption("PPP • Interest Rate Parity & Carry Trade • International Fisher Effect")

SERIES = {
    "spot": "EXINUS",
    "india_cpi": "INDCPIALLMINMEI",
    "us_cpi": "CPIAUCNS",
    "india_rate": "INDIR3TIB01STM",
    "us_rate": "TB3MS",
}
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"

@st.cache_data(ttl=86400, show_spinner="Downloading monthly FRED observations…")
def load_fred(series_id):
    df = pd.read_csv(FRED_URL.format(series_id))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    return df.dropna().set_index("date")

@st.cache_data(ttl=86400, show_spinner=False)
def get_data():
    frames = [load_fred(s) for s in SERIES.values()]
    data = pd.concat(frames, axis=1).sort_index()
    data = data.resample("MS").mean()
    # Keep all dates; theory-specific calculations use available common observations.
    data["india_inflation_yoy"] = data[SERIES["india_cpi"]].pct_change(12) * 100
    data["us_inflation_yoy"] = data[SERIES["us_cpi"]].pct_change(12) * 100
    data["inflation_diff_pp"] = data["india_inflation_yoy"] - data["us_inflation_yoy"]
    data["interest_diff_pp"] = data[SERIES["india_rate"]] - data[SERIES["us_rate"]]
    data["spot_change_yoy_pct"] = (data[SERIES["spot"]] / data[SERIES["spot"]].shift(12) - 1) * 100
    data["spot_appreciation_inr_pct"] = -data["spot_change_yoy_pct"]
    return data

try:
    raw = get_data()
except Exception as e:
    st.error("FRED data could not be loaded. Check your internet connection and try again.")
    st.exception(e)
    st.stop()

st.sidebar.header("Dashboard controls")
min_date = raw.index.min().date()
max_date = raw.index.max().date()
start = st.sidebar.date_input("Start date", value=max(min_date, date(2012,1,1)), min_value=min_date, max_value=max_date)
end = st.sidebar.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)
if start > end:
    st.error("Start date must be before end date.")
    st.stop()
df = raw.loc[str(start):str(end)].copy()

st.sidebar.markdown("---")
st.sidebar.markdown("**Quote convention:** INR per 1 USD. A rise in the exchange rate means INR depreciation.")
st.sidebar.markdown("**Sources:** Federal Reserve Bank of St. Louis FRED; underlying sources include Federal Reserve, BLS and OECD.")

tab1, tab2, tab3, tab4 = st.tabs(["1. PPP & Misalignment", "2. IRP & Carry Trade", "3. International Fisher Effect", "Data & Methodology"])

# PPP: common CPI dates; anchor at first common observation in selected period.
with tab1:
    st.subheader("Relative Purchasing Power Parity")
    p = df[[SERIES["spot"], SERIES["india_cpi"], SERIES["us_cpi"]]].dropna().copy()
    if len(p) < 2:
        st.warning("Insufficient overlapping spot-rate and CPI observations for the selected dates.")
    else:
        base_spot = p.iloc[0][SERIES["spot"]]
        base_india_cpi = p.iloc[0][SERIES["india_cpi"]]
        base_us_cpi = p.iloc[0][SERIES["us_cpi"]]
        p["ppp_implied"] = base_spot * (p[SERIES["india_cpi"]] / base_india_cpi) / (p[SERIES["us_cpi"]] / base_us_cpi)
        p["misalignment_pct"] = (p[SERIES["spot"]] / p["ppp_implied"] - 1) * 100
        latest = p.iloc[-1]
        mis = latest["misalignment_pct"]
        status = ("INR undervalued vs USD" if mis > 0.5 else
                  "INR overvalued vs USD" if mis < -0.5 else "INR approximately at PPP")
        c1,c2,c3 = st.columns(3)
        c1.metric("Latest actual spot", f"₹{latest[SERIES['spot']]:.4f} / USD")
        c2.metric("PPP-implied spot", f"₹{latest['ppp_implied']:.4f} / USD")
        c3.metric("INR misalignment", f"{abs(mis):.2f}%", delta=status, delta_color="inverse" if mis > 0 else "normal")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=p.index, y=p[SERIES["spot"]], name="Actual spot (INR/USD)", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=p.index, y=p["ppp_implied"], name="PPP-implied spot", line=dict(width=2, dash="dash")))
        fig.update_layout(title="Actual Spot Rate vs Relative PPP-Implied Spot Rate", xaxis_title="Month", yaxis_title="INR per USD", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Base month: {p.index[0]:%b %Y}. Misalignment = (Actual − PPP) / PPP × 100. Positive means actual INR/USD is above PPP: INR is weaker (undervalued) relative to the PPP benchmark.")
        st.line_chart(p["misalignment_pct"].rename("Misalignment (%)"))

# IRP/carry tracker
with tab2:
    st.subheader("Interest Rate Differential, UIP and Uncovered Carry Trade")
    cols = [SERIES["spot"], SERIES["india_rate"], SERIES["us_rate"]]
    q = df[cols].dropna().copy()
    q["interest_diff_pp"] = q[SERIES["india_rate"]] - q[SERIES["us_rate"]]
    q["interest_diff_start_pp"] = q["interest_diff_pp"].shift(12)
    q["spot_change_yoy_pct"] = (q[SERIES["spot"]] / q[SERIES["spot"]].shift(12) - 1) * 100
    # A positive spot change is INR depreciation because quote is INR/USD.
    # Use the yields observed at the start of the 12-month holding period.
    q["carry_return_pct"] = ((1 + q[SERIES["india_rate"]].shift(12)/100) /
                              (1 + q[SERIES["us_rate"]].shift(12)/100) *
                              (q[SERIES["spot"]].shift(12) / q[SERIES["spot"]]) - 1) * 100
    q["uip_gap_pp"] = q["interest_diff_start_pp"] - q["spot_change_yoy_pct"]
    q = q.dropna(subset=["spot_change_yoy_pct", "carry_return_pct", "interest_diff_start_pp"])
    if q.empty:
        st.warning("At least 12 months of overlapping interest-rate and spot observations are needed.")
    else:
        latest = q.iloc[-1]
        a,b,c = st.columns(3)
        a.metric("Start-of-period India − US yield spread", f"{latest['interest_diff_start_pp']:.2f} pp")
        b.metric("12-month INR depreciation", f"{latest['spot_change_yoy_pct']:.2f}%")
        c.metric("Uncovered carry return (USD-funded)", f"{latest['carry_return_pct']:.2f}%")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=q.index, y=q["interest_diff_start_pp"], name="Start-of-period interest differential (pp)"), secondary_y=False)
        fig.add_trace(go.Scatter(x=q.index, y=q["spot_change_yoy_pct"], name="INR depreciation (12m, %)"), secondary_y=True)
        fig.update_layout(title="Yield Differential vs Annual INR Spot Depreciation", hovermode="x unified")
        fig.update_yaxes(title_text="Interest differential (percentage points)", secondary_y=False)
        fig.update_yaxes(title_text="INR depreciation (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
        st.line_chart(q["carry_return_pct"].rename("USD-funded INR carry return (%)"))
        st.caption("Carry return assumes borrowing USD at the US 3-month Treasury yield, investing INR at the India 3-month interbank rate, and converting back at the observed 12-month-ahead spot rate. It is an illustrative historical proxy, not a tradable backtest; transaction costs, forward hedging, taxes and credit/liquidity risk are excluded.")
        st.write("UIP diagnostic: compare the India–US nominal interest differential with the realised 12-month rise in INR per USD. A positive UIP gap means the interest spread exceeded realised INR depreciation.")
        st.metric("Latest UIP gap (start yield spread − realised depreciation)", f"{latest['uip_gap_pp']:.2f} pp")

# IFE
with tab3:
    st.subheader("International Fisher Effect Diagnostic")
    z = df[["inflation_diff_pp", "interest_diff_pp"]].dropna()
    if len(z) < 3:
        st.warning("Not enough overlapping inflation and interest-rate observations for a meaningful diagnostic.")
    else:
        corr = z["inflation_diff_pp"].corr(z["interest_diff_pp"])
        slope, intercept = np.polyfit(z["inflation_diff_pp"], z["interest_diff_pp"], 1)
        z["fitted"] = intercept + slope*z["inflation_diff_pp"]
        x = z["inflation_diff_pp"].to_numpy()
        y = z["interest_diff_pp"].to_numpy()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", name="Monthly observations", opacity=.65))
        xs = np.linspace(np.nanmin(x), np.nanmax(x), 100)
        fig.add_trace(go.Scatter(x=xs, y=intercept+slope*xs, mode="lines", name="OLS trend"))
        fig.update_layout(title="Inflation Differential vs Nominal Interest Differential", xaxis_title="India − US inflation differential (pp, YoY)", yaxis_title="India − US nominal interest differential (pp)", hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)
        m1,m2,m3 = st.columns(3)
        m1.metric("Correlation", f"{corr:.3f}")
        m2.metric("Regression slope", f"{slope:.3f}")
        m3.metric("Observations", f"{len(z):,}")
        st.caption("IFE suggests nominal interest-rate differentials should broadly reflect expected inflation differentials. This chart uses realised year-on-year CPI inflation as a proxy for expected inflation; it is a diagnostic, not a direct measure of expectations.")
        st.write(f"Estimated relationship: Interest differential = {intercept:.3f} + ({slope:.3f} × inflation differential).")

with tab4:
    st.subheader("Data coverage and source mapping")
    mapping = pd.DataFrame([
        ["INR/USD spot rate", "EXINUS", "Monthly average, INR per USD", "Board of Governors / FRED"],
        ["India CPI", "INDCPIALLMINMEI", "Monthly CPI index, 2015=100", "OECD via FRED"],
        ["US CPI", "CPIAUCNS", "Monthly CPI index, not seasonally adjusted", "US BLS via FRED"],
        ["India interest rate", "INDIR3TIB01STM", "3-month interbank rate, % p.a.", "OECD via FRED"],
        ["US interest rate", "TB3MS", "3-month Treasury bill secondary market rate, % p.a.", "US Treasury/Federal Reserve via FRED"],
    ], columns=["Variable", "FRED ID", "Frequency / unit", "Underlying source"])
    st.dataframe(mapping, use_container_width=True, hide_index=True)
    st.warning("The India CPI FRED series INDCPIALLMINMEI ends in March 2025 in the currently documented series. Therefore PPP and IFE calculations stop at the latest overlapping CPI month. Do not interpret missing later values as zero.")
    st.write("The app aligns series by monthly date and uses available common observations. Interest-rate and CPI measures are proxies with different underlying definitions; note this in your interpretation.")
    st.write("Download the aligned dataset below. It includes source series and derived variables.")
    st.download_button("Download compiled INR–USD dataset (CSV)", data=raw.to_csv(index_label="date").encode("utf-8"), file_name="INR_USD_FRED_monthly_dataset.csv", mime="text/csv")
    st.write("Raw data source pages:")
    st.markdown("""
    - [EXINUS – INR per USD, monthly](https://fred.stlouisfed.org/series/EXINUS)
    - [INDCPIALLMINMEI – India CPI](https://fred.stlouisfed.org/series/INDCPIALLMINMEI)
    - [CPIAUCNS – US CPI, NSA](https://fred.stlouisfed.org/series/CPIAUCNS)
    - [INDIR3TIB01STM – India 3-month interbank rate](https://fred.stlouisfed.org/series/INDIR3TIB01STM)
    - [TB3MS – US 3-month Treasury bill rate](https://fred.stlouisfed.org/series/TB3MS)
    """)
    st.write(f"Current data rows: {len(raw):,} | From {raw.index.min():%b %Y} to {raw.index.max():%b %Y}.")
