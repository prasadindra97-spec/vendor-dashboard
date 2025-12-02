import streamlit as st
import pandas as pd
import datetime
import altair as alt

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(
    page_title="Vendor Price & Score Dashboard",
    layout="wide"
)

# Set password securely through Streamlit Secrets
# (streamlit cloud → settings → secrets)
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")  


# ----------------------------
# LOGIN SCREEN
# ----------------------------
def login_screen():
    st.title("🔒 Secure Login")

    pw = st.text_input("Enter password:", type="password")

    if pw == APP_PASSWORD:
        st.session_state["auth"] = True
        st.success("Login successful!")
    elif pw:
        st.error("Incorrect password.")

    st.stop()


if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    login_screen()


# ----------------------------
# PAYMENT TERMS RECALCULATION
# ----------------------------
def recalc_terms_days(term_raw):
    """Calculate terms into numeric days based on today's date."""
    if pd.isna(term_raw):
        return 0

    term_raw = str(term_raw).strip()
    today = datetime.date.today()

    if "No current vendor" in term_raw:
        return 0

    if "30 day" in term_raw:
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

    return 0


# ----------------------------
# SAFE SCORE CALCULATION
# ----------------------------
def calculate_vendor_score(row):
    """Calculate vendor score or return None if invalid."""
    # ---- Clean price ----
    raw_price = str(row.get("price", "")).strip()
    if raw_price in ["", " ", None, "nan", "NaN"]:
        return None

    try:
        price = float(raw_price)
    except:
        return None

    # ---- Clean terms ----
    try:
        days = int(row["terms_days"])
    except:
        days = 0

    if days <= 0:
        return None

    # ---- Score formula ----
    return price + (1 / days)


# ----------------------------
# RANKING WITH BADGES
# ----------------------------
def assign_rank_badge(df):
    df = df.copy()

    # Rank only non-null scores
    df["rank"] = (
        df["vendor_score"]
        .where(df["vendor_score"].notnull())
        .rank(method="first")
        .astype("Int64")
    )

    def badge(r):
        if pd.isna(r):
            return ""
        if r == 1: return "🥇 Gold"
        if r == 2: return "🥈 Silver"
        if r == 3: return "🥉 Bronze"
        return ""

    df["rank_badge"] = df["rank"].apply(badge)
    return df


# ----------------------------
# START APP
# ----------------------------
st.title("📊 Vendor Pricing, Terms & Score Dashboard")

uploaded_file = st.file_uploader("Upload master_pricing_clean.csv", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Auto-recalc terms
    df["terms_days"] = df["terms_raw"].apply(recalc_terms_days)

    # Score
    df["vendor_score"] = df.apply(calculate_vendor_score, axis=1)

    st.success("Dataset loaded correctly!")

    # ------------------------------
    # PRODUCT SELECTION
    # ------------------------------
    product_list = sorted(df["product"].unique())
    selected_product = st.selectbox("Select Product", product_list)

    product_df = df[df["product"] == selected_product].copy()

    # ---------------------------------------
    # ORDER QUANTITY INPUT
    # ---------------------------------------
    st.subheader("📦 Enter Order Quantity")
    order_qty = st.number_input("Order Quantity", min_value=1, value=1000)

    # Compute total cost
    product_df["total_cost"] = product_df["price"].astype(float) * order_qty

    # Rank vendors
    product_df = assign_rank_badge(product_df)

    # ------------------------------
    # EDITOR
    # ------------------------------
    st.subheader(f"🛠 Edit Vendor Data – {selected_product}")

    edited_df = st.data_editor(
        product_df,
        width="stretch",
        hide_index=True
    )

    # Recalculate after edits
    edited_df["terms_days"] = edited_df["terms_raw"].apply(recalc_terms_days)
    edited_df["vendor_score"] = edited_df.apply(calculate_vendor_score, axis=1)
    edited_df["total_cost"] = edited_df["price"].astype(float) * order_qty
    edited_df = assign_rank_badge(edited_df)

    # ------------------------------
    # VISUALS
    # ------------------------------

    # Price chart
    st.subheader("📉 Price Comparison")
    price_chart = (
        alt.Chart(edited_df)
        .mark_bar()
        .encode(
            x=alt.X("vendor_code:N", title="Vendor"),
            y=alt.Y("price:Q", title="Unit Price"),
            color="vendor_code:N",
            tooltip=["vendor_code", "price"]
        )
        .properties(height=350)
    )
    st.altair_chart(price_chart, use_container_width=True)

    # Score chart
    st.subheader("🏆 Vendor Score (Lower = Better)")
    score_chart = (
        alt.Chart(edited_df.dropna(subset=["vendor_score"]))
        .mark_bar()
        .encode(
            x=alt.X("vendor_code:N"),
            y=alt.Y("vendor_score:Q"),
            color="vendor_code:N",
            tooltip=["vendor_code", "vendor_score"]
        )
        .properties(height=350)
    )
    st.altair_chart(score_chart, use_container_width=True)

    # Total cost chart
    st.subheader("💰 Total Cost Comparison")
    cost_chart = (
        alt.Chart(edited_df)
        .mark_bar()
        .encode(
            x="vendor_code:N",
            y="total_cost:Q",
            color="vendor_code:N",
            tooltip=["vendor_code", "total_cost"]
        )
        .properties(height=350)
    )
    st.altair_chart(cost_chart, use_container_width=True)

    # ------------------------------
    # SAVE UPDATED FILE
    # ------------------------------
    st.subheader("💾 Download Updated File")

    df.update(edited_df)
    csv_data = df.to_csv(index=False)

    st.download_button(
        label="⬇ Download master_pricing_clean_updated.csv",
        data=csv_data,
        file_name="master_pricing_clean_updated.csv",
        mime="text/csv"
    )

else:
    st.info("Upload your master_pricing_clean.csv to continue.")
