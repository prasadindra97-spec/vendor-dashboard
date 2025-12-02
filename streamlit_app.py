import streamlit as st
import pandas as pd
import datetime
import altair as alt

# ------------------------------------------------
# LOAD PASSWORD SECURELY FROM STREAMLIT SECRETS
# ------------------------------------------------
APP_PASSWORD = st.secrets.get("app_password", None)

st.set_page_config(
    page_title="Vendor Pricing Dashboard",
    layout="wide"
)

# ------------------------------------------------
# LOGIN SCREEN
# ------------------------------------------------
def login_screen():
    st.title("🔒 Secure Login")

    pw = st.text_input("Enter password:", type="password")

    if pw and APP_PASSWORD and pw == APP_PASSWORD:
        st.session_state["auth"] = True
        st.success("Login successful! Loading dashboard…")
        st.rerun()

    elif pw:
        st.error("Incorrect password.")

    st.stop()


if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    login_screen()


# ------------------------------------------------
# FUNCTIONS
# ------------------------------------------------

def recalc_terms_days(term_raw):
    """Recalculate payment terms based on today's date."""
    if pd.isna(term_raw):
        return 0

    term_raw = str(term_raw).strip()
    today = datetime.date.today()

    if "No current vendor" in term_raw:
        return 0

    # Straight numeric terms (30 day terms)
    if "30" in term_raw:
        return 30

    # August 1st terms
    if "August 1st" in term_raw:
        due = datetime.date(today.year, 8, 1)
        if due < today:
            due = datetime.date(today.year + 1, 8, 1)
        return (due - today).days

    # March 15th terms
    if "March 15th" in term_raw:
        due = datetime.date(today.year, 3, 15)
        if due < today:
            due = datetime.date(today.year + 1, 3, 15)
        return (due - today).days

    return 0


def calculate_vendor_score(row):
    """Lower score = better vendor."""
    try:
        price = float(row["price"])
    except:
        return 9999

    days = int(row["terms_days"]) if row["terms_days"] else 0
    return price + (1 / days) if days > 0 else 9999


# ------------------------------------------------
# RANKING & BADGES
# ------------------------------------------------
def assign_rank_badge(df):
    df = df.copy()
    df["rank"] = df["vendor_score"].rank(method="first").astype(int)

    def badge_for_rank(r):
        if r == 1:
            return "🥇 Gold"
        elif r == 2:
            return "🥈 Silver"
        elif r == 3:
            return "🥉 Bronze"
        return ""

    def color_for_rank(r):
        if r == 1:
            return "background-color: #fff4b3;"  # gold tint
        elif r == 2:
            return "background-color: #e6e8ea;"  # silver tint
        elif r == 3:
            return "background-color: #f2d3b1;"  # bronze tint
        return ""

    df["rank_badge"] = df["rank"].apply(badge_for_rank)
    df["rank_color"] = df["rank"].apply(color_for_rank)
    return df


# ------------------------------------------------
# APP INTERFACE
# ------------------------------------------------

st.title("📊 Vendor Pricing, Terms & Score Dashboard")

uploaded_file = st.file_uploader("Upload master_pricing_clean.csv", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    # Auto-recompute days
    df["terms_days"] = df["terms_raw"].apply(recalc_terms_days)

    # Compute vendor score
    df["vendor_score"] = df.apply(calculate_vendor_score, axis=1)

    st.success("Dataset loaded successfully!")

    # Product selector
    products = sorted(df["product"].unique())
    selected_product = st.selectbox("Select Product", products)

    product_df = df[df["product"] == selected_product].copy()

    st.subheader(f"🛠 Edit Pricing & Terms — {selected_product}")

    edited_df = st.data_editor(
        product_df,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )

    # Recalculate after editing
    edited_df["terms_days"] = edited_df["terms_raw"].apply(recalc_terms_days)
    edited_df["vendor_score"] = edited_df.apply(calculate_vendor_score, axis=1)

    # Ranking
    ranked_df = assign_rank_badge(edited_df)

    # ------------------------------------------------
    # CHARTS
    # ------------------------------------------------

    st.subheader("📉 Vendor Price Comparison")

    price_chart = (
        alt.Chart(ranked_df)
        .mark_bar()
        .encode(
            x=alt.X("vendor_code:N", sort=None, title="Vendor"),
            y=alt.Y("price:Q", title="Price ($)", scale=alt.Scale(domainPadding=20)),
            tooltip=["vendor_code", "price"]
        )
        .properties(height=350)
    )
    st.altair_chart(price_chart, use_container_width=True)

    st.subheader("🏆 Vendor Score Comparison")

    score_chart = (
        alt.Chart(ranked_df)
        .mark_bar()
        .encode(
            x=alt.X("vendor_code:N", sort=None),
            y=alt.Y("vendor_score:Q", title="Vendor Score", scale=alt.Scale(domainPadding=20)),
            tooltip=["vendor_code", "vendor_score", "rank_badge"]
        )
        .properties(height=350)
    )
    st.altair_chart(score_chart, use_container_width=True)

    # ------------------------------------------------
    # CEO: Order Quantity → Total Cost
    # ------------------------------------------------

    st.subheader("📦 Order Cost Comparison")

    qty = st.number_input("Enter order quantity:", min_value=1, value=100)

    ranked_df["total_cost"] = ranked_df["price"].astype(float) * qty

    order_chart = (
        alt.Chart(ranked_df)
        .mark_bar()
        .encode(
            x="vendor_code:N",
            y=alt.Y("total_cost:Q", title="Total Cost ($)"),
            tooltip=["vendor_code", "price", "total_cost"]
        )
        .properties(height=300)
    )
    st.altair_chart(order_chart, use_container_width=True)

    # ------------------------------------------------
    # Ranking Table
    # ------------------------------------------------

    st.subheader("🏅 Vendor Ranking Table")

    def style_rows(row):
        return [row["rank_color"]] * len(row)

    styled = ranked_df[["vendor_code", "price", "terms_raw", "terms_days",
                        "vendor_score", "rank", "rank_badge"]].style.apply(style_rows, axis=1)

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # ------------------------------------------------
    # SAVE UPDATED DATA
    # ------------------------------------------------
    st.subheader("💾 Save Updated Dataset")

    df.update(edited_df)
    updated_data = df.to_csv(index=False)

    st.download_button(
        label="⬇ Download Updated CSV",
        data=updated_data,
        file_name="master_pricing_clean_updated.csv",
        mime="text/csv"
    )

else:
    st.info("Please upload your master_pricing_clean.csv file to begin.")
