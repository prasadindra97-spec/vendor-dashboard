import streamlit as st
import pandas as pd
import datetime
import altair as alt

# ----------------------------
# LOAD PASSWORD FROM SECRETS
# ----------------------------
APP_PASSWORD = st.secrets["APP_PASSWORD"]

st.set_page_config(
    page_title="Vendor Price & Score Dashboard",
    layout="wide"
)

# ----------------------------
# LOGIN SCREEN
# ----------------------------
def login_screen():
    st.title("🔒 Secure Login")

    pw = st.text_input("Enter password:", type="password")

    if pw == APP_PASSWORD:
        st.session_state["auth"] = True
        st.success("Login successful! Loading dashboard...")
        st.rerun()   # modern Streamlit
    elif pw:
        st.error("Incorrect password.")

    st.stop()


if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    login_screen()


# ----------------------------
# FUNCTIONS
# ----------------------------
def recalc_terms_days(term_raw):
    """Recalculate payment terms based on today's date."""
    if pd.isna(term_raw):
        return 0

    term_raw = str(term_raw).strip()
    today = datetime.date.today()

    if "No current vendor" in term_raw:
        return 0

    if term_raw.startswith("30"):
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


def calculate_vendor_score(row):
    days = float(row["terms_days"])
    price = float(row["price"])
    return price + (1 / days) if days > 0 else 9999


# ----------------------------
# APP UI
# ----------------------------
st.title("📊 Vendor Pricing, Terms & Score Dashboard")

st.write("Upload your base dataset (master_pricing_clean.csv):")
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Auto-refresh terms_days every load
    df["terms_days"] = df["terms_raw"].apply(recalc_terms_days)

    # Compute score
    df["vendor_score"] = df.apply(calculate_vendor_score, axis=1)

    st.success("Dataset loaded successfully!")

    # ------------------------------
    # PRODUCT FILTER
    # ------------------------------
    product_list = sorted(df["product"].unique())
    selected_product = st.selectbox("Select Product", product_list)

    product_df = df[df["product"] == selected_product].copy()

    st.subheader(f"🛠 Edit Pricing & Terms — {selected_product}")

    edited_df = st.data_editor(
        product_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    # Recalculate scores after edits
    edited_df["terms_days"] = edited_df["terms_raw"].apply(recalc_terms_days)
    edited_df["vendor_score"] = edited_df.apply(calculate_vendor_score, axis=1)

    # ------------------------------
    # CEO ENTERS QUANTITY
    # ------------------------------
    st.subheader("🧮 Calculate Order Cost")
    qty = st.number_input("Enter quantity to order:", min_value=1, value=100)

    edited_df["total_cost"] = edited_df["price"].fillna(0) * qty

    # Ranking vendors
    ranked = edited_df[edited_df["price"].notna()].copy()
    ranked["rank"] = ranked["total_cost"].rank(method="dense")

    st.subheader("🏆 Best Vendors (Based on Total Cost)")
    best_table = ranked.sort_values("rank")[["vendor_code", "price", "total_cost", "rank"]]
    st.dataframe(best_table)

    # ------------------------------
    # PRICE CHART WITH FIXED AXIS RANGE
    # ------------------------------
    st.subheader("📉 Vendor Price Comparison")

    chart = (
        alt.Chart(edited_df)
        .mark_bar()
        .encode(
            x=alt.X("vendor_code:N", title="Vendor"),
            y=alt.Y("price:Q", scale=alt.Scale(domain=[0, edited_df["price"].max() + 0.2])),
            tooltip=["vendor_code", "price"]
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    # ------------------------------
    # TOTAL COST CHART
    # ------------------------------
    st.subheader("💰 Total Cost Comparison")

    cost_chart = (
        alt.Chart(edited_df)
        .mark_bar(color="green")
        .encode(
            x="vendor_code:N",
            y="total_cost:Q",
            tooltip=["vendor_code", "total_cost"]
        )
        .properties(height=400)
    )

    st.altair_chart(cost_chart, use_container_width=True)

    # ------------------------------
    # SAVE UPDATED FILE
    # ------------------------------
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
