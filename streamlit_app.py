import streamlit as st
import pandas as pd
import datetime

# -----------------------------------------------------
# SECURE LOGIN (via Streamlit Secrets)
# -----------------------------------------------------
try:
    APP_PASSWORD = st.secrets["PASSWORD"]
except:
    APP_PASSWORD = None

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
        st.error("❗ PASSWORD missing in Streamlit Secrets. Add it in Settings → Secrets.")
        st.stop()

    pw = st.text_input("Enter password:", type="password")

    if pw == APP_PASSWORD:
        st.session_state["auth"] = True
        st.success("Login successful! Redirecting...")
        st.rerun()
    elif pw:
        st.error("Incorrect password.")

    st.stop()


if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    login_screen()


# -----------------------------------------------------
# SAFE CLEANERS
# -----------------------------------------------------
def clean_price(x):
    """Remove spaces, empty values, convert to float safely."""
    try:
        x = str(x).strip()
        if x == "" or x.lower() in ["none", "nan"]:
            return None
        return float(x)
    except:
        return None


def recalc_terms_days(term_raw):
    if pd.isna(term_raw):
        return None

    term_raw = str(term_raw).strip()
    today = datetime.date.today()

    if term_raw == "" or term_raw.lower() == "none":
        return None

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
    price = clean_price(row["price"])
    days = row["terms_days"]

    if price is None or days is None or days == 0:
        return None

    return round(price + (1 / days), 4)


# -----------------------------------------------------
# MAIN APP
# -----------------------------------------------------
st.title("📊 Vendor Pricing, Terms & Score Dashboard")

uploaded_file = st.file_uploader("Upload master_pricing_clean.csv", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # CLEAN PRICE FIRST
    df["price"] = df["price"].apply(clean_price)

    # CLEAN TERMS
    df["terms_days"] = df["terms_raw"].apply(recalc_terms_days)

    # SCORE
    df["vendor_score"] = df.apply(calculate_vendor_score, axis=1)

    st.success("Dataset loaded successfully!")

    # -----------------------
    # PRODUCT FILTER
    # -----------------------
    product_list = sorted(df["product"].unique())
    selected_product = st.selectbox("Select Product", product_list)

    product_df = df[df["product"] == selected_product].copy()

    st.subheader(f"🧾 Edit Pricing & Terms – {selected_product}")

    edited_df = st.data_editor(
        product_df,
        width="stretch",
        hide_index=True
    )

    # CLEAN AGAIN AFTER EDITS
    edited_df["price"] = edited_df["price"].apply(clean_price)
    edited_df["terms_days"] = edited_df["terms_raw"].apply(recalc_terms_days)
    edited_df["vendor_score"] = edited_df.apply(calculate_vendor_score, axis=1)

    # -----------------------
    # CEO ORDER QUANTITY
    # -----------------------
    st.subheader("📦 CEO Order Quantity")
    qty = st.number_input("Enter quantity to order:", min_value=1, value=100)

    edited_df["total_cost"] = edited_df["price"] * qty

    # -----------------------
    # RANKING
    # -----------------------
    ranking = edited_df.dropna(subset=["vendor_score"]).copy()
    ranking = ranking.sort_values("vendor_score")

    medals = ["🥇", "🥈", "🥉"]
    ranking["rank"] = [medals[i] if i < 3 else "" for i in range(len(ranking))]

    st.subheader("🏆 Vendor Ranking")
    st.dataframe(
        ranking[["rank", "vendor_code", "price", "terms_days", "vendor_score", "total_cost"]],
        width="stretch"
    )

    # -----------------------
    # VISUALS
    # -----------------------
    st.subheader("📉 Price Comparison")
    st.bar_chart(edited_df.set_index("vendor_code")["price"])

    st.subheader("💰 Total Cost Comparison")
    st.bar_chart(edited_df.set_index("vendor_code")["total_cost"])

    # -----------------------
    # DOWNLOAD UPDATED FILE
    # -----------------------
    df.update(edited_df)

    st.download_button(
        "⬇ Download Updated CSV",
        df.to_csv(index=False),
        "updated_master_pricing_clean.csv",
        "text/csv"
    )

else:
    st.info("Upload your CSV file to begin.")
