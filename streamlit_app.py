import streamlit as st
import pandas as pd
import datetime

# -----------------------------------------------------
# SECURE LOGIN USING STREAMLIT SECRETS
# -----------------------------------------------------
# Ensure your Streamlit Cloud Secrets contains:
# PASSWORD = "winbio2025"
APP_PASSWORD = st.secrets.get("PASSWORD", None)

st.set_page_config(
    page_title="Vendor Price & Score Dashboard",
    layout="wide"
)

# -----------------------------------------------------
# LOGIN SCREEN
# -----------------------------------------------------
def login_screen():
    st.title("🔒 Secure Login")

    if APP_PASSWORD is None:
        st.error("❗ Password missing in Streamlit Secrets. Add it in Settings → Secrets.")
        st.stop()

    pw = st.text_input("Enter password:", type="password")

    if pw == APP_PASSWORD:
        st.session_state["auth"] = True
        st.success("Login successful!")
        st.rerun()
    elif pw:
        st.error("Incorrect password.")

    st.stop()


if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    login_screen()


# -----------------------------------------------------
# DATA CLEANING FUNCTIONS
# -----------------------------------------------------
def clean_price(x):
    """Converts price to float or None safely."""
    try:
        return float(str(x).strip())
    except:
        return None


def recalc_terms_days(term_raw):
    """Recalculate vendor payment terms."""
    if pd.isna(term_raw) or str(term_raw).strip() == "":
        return None

    term_raw = str(term_raw).strip()
    today = datetime.date.today()

    if "No current vendor" in term_raw:
        return None

    if "30" in term_raw:
        return 30

    if "August 1st" in term_raw:
        due = datetime.date(today.year, 8, 1)
        if due < today:
            due = datetime.date(today.year + 1, 8, 1)
        return (due - today).days

    if "March 15th" in term_raw:
        due = datetime.date(today.year, 3, 15)
        if due < today:
            due = datetime.date(today.year + 1, 3, 15)
        return (due - today).days

    return None


def calculate_vendor_score(row):
    """Lower score = better"""
    price = clean_price(row["price"])
    days = row["terms_days"]

    if price is None or days is None or days == 0:
        return None

    return round(price + (1 / days), 4)


# -----------------------------------------------------
# MAIN APP
# -----------------------------------------------------
st.title("📊 Vendor Pricing, Terms & Score Dashboard")

st.write("Upload your base dataset (master_pricing_clean.csv):")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # CLEAN PRICE COLUMN FIRST
    df["price"] = df["price"].apply(clean_price)

    # RECALCULATE TERMS
    df["terms_days"] = df["terms_raw"].apply(recalc_terms_days)

    # CALCULATE SCORE
    df["vendor_score"] = df.apply(calculate_vendor_score, axis=1)

    st.success("Dataset loaded successfully!")

    # ---------------------------------------
    # PRODUCT SELECTION
    # ---------------------------------------
    product_list = sorted(df["product"].unique())
    selected_product = st.selectbox("Select Product", product_list)

    product_df = df[df["product"] == selected_product].copy()

    st.subheader(f"🛠 Edit Pricing & Terms – {selected_product}")

    edited_df = st.data_editor(
        product_df,
        width="stretch",
        hide_index=True
    )

    # RE-CLEAN AND RE-SCORE AFTER EDITING
    edited_df["price"] = edited_df["price"].apply(clean_price)
    edited_df["terms_days"] = edited_df["terms_raw"].apply(recalc_terms_days)
    edited_df["vendor_score"] = edited_df.apply(calculate_vendor_score, axis=1)

    # ---------------------------------------
    # CEO QUANTITY INPUT
    # ---------------------------------------
    st.subheader("📦 CEO Order Quantity Input")
    qty = st.number_input("Enter quantity to order:", min_value=1, value=100)

    edited_df["total_cost"] = edited_df["price"] * qty

    # RANKING
    ranking_df = edited_df[edited_df["vendor_score"].notna()].copy()
    ranking_df = ranking_df.sort_values("vendor_score")

    def medal(i):
        return "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else ""

    ranking_df["rank"] = [medal(i) for i in range(len(ranking_df))]

    st.subheader("🏆 Vendor Ranking (Lower Score = Better)")
    st.dataframe(
        ranking_df[["rank", "vendor_code", "price", "terms_days", "vendor_score", "total_cost"]],
        width="stretch"
    )

    # ---------------------------------------
    # VISUALS
    # ---------------------------------------
    st.subheader("📉 Vendor Price Comparison")
    st.bar_chart(
        edited_df.set_index("vendor_code")["price"],
        height=300
    )

    st.subheader("📈 Total Cost Comparison (Qty × Price)")
    st.bar_chart(
        edited_df.set_index("vendor_code")["total_cost"],
        height=300
    )

    # ---------------------------------------
    # SAVE UPDATED FILE
    # ---------------------------------------
    st.subheader("💾 Save Updated Data")

    df.update(edited_df)

    csv_data = df.to_csv(index=False)

    st.download_button(
        label="⬇ Download Updated master_pricing_clean.csv",
        data=csv_data,
        file_name="master_pricing_clean_updated.csv",
        mime="text/csv"
    )

else:
    st.info("Please upload your master_pricing_clean.csv file to start.")
