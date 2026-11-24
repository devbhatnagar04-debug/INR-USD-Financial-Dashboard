INR–USD International Financial Management Dashboard

FILES
- streamlit_app.py: complete three-tab dashboard plus data/methodology tab
- requirements.txt: Python packages

RUN LOCALLY
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run: pip install -r requirements.txt
4. Run: streamlit run streamlit_app.py
5. The app downloads monthly series from FRED when launched. Internet access is required.
6. In the Data & Methodology tab, click Download compiled INR–USD dataset (CSV).

DEPLOY
Push this folder to a GitHub repository. On Streamlit Community Cloud, create an app
from the repository and select streamlit_app.py as the entry point. Copy the resulting
public app URL into Google Classroom.

IMPORTANT DATA NOTE
The India CPI series INDCPIALLMINMEI currently ends March 2025 in the FRED catalogue.
PPP and IFE therefore stop at the latest common CPI observation. The spot and interest
rate series may have more recent observations. This is intentional; no CPI values are
fabricated or extrapolated.

QUOTE CONVENTION
Exchange rate is INR per USD. A rise means INR depreciation; a fall means INR appreciation.

ACADEMIC LIMITATIONS
- CPI ratio is used as a relative PPP proxy.
- India 3-month interbank rate and US 3-month Treasury bill rate are not perfectly
  identical instruments; treat the spread as a proxy.
- IFE uses realised YoY CPI inflation as a proxy for expected inflation.
- Carry return is a simplified historical USD-funded INR carry illustration and excludes
  transaction costs, bid-ask spreads, taxes, collateral, default and liquidity risk.
