import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Oasis HOA 2026 Budget", layout="wide")

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "Oasis2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Please enter the Homeowner Access Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error.
        st.text_input(
            "Please enter the Homeowner Access Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():
    # --- DATA LOADING ---
    @st.cache_data
    def load_data():
        # Loading the provided CSV
        try:
            df = pd.read_csv('Oasis HOA Yearly Budget and Actuals.csv')
            # Clean up column names and fill NaNs
            df['2026 Budget'] = pd.to_numeric(df['2026 Budget'], errors='coerce').fillna(0)
            df['2025 Actuals'] = pd.to_numeric(df['2025 Actuals'], errors='coerce').fillna(0)
            df['2024 Actuals'] = pd.to_numeric(df['2024 Actuals'], errors='coerce').fillna(0)
            df['2026 Notes'] = df['2026 Notes'].fillna("No justification provided.")
            return df
        except FileNotFoundError:
            st.error("Data file not found. Please ensure 'Oasis HOA Yearly Budget and Actuals.csv' is in the repository.")
            return pd.DataFrame()

    df = load_data()

    if not df.empty:
        # --- CURRENCY LOGIC ---
        # Using fixed rates for deployment simplicity as requested
        st.sidebar.header("Settings")
        currency = st.sidebar.selectbox("Select Currency", ["MXN", "USD", "CAD"])

        # Fixed exchange rates (Locked for the 2026 Assembly)
        rates = {"MXN": 1.0, "USD": 0.058, "CAD": 0.079}
        symbol = {"MXN": "$", "USD": "US$", "CAD": "CA$"}

        def convert(val):
            return val * rates[currency]

        # Apply conversions to temporary columns for display
        df_disp = df.copy()
        val_cols = ['2024 Actuals', '2025 Actuals', '2026 Budget']
        for col in val_cols:
            df_disp[col] = df_disp[col].apply(convert)

        # --- CALCULATIONS ---
        df_disp['Increase_Amt'] = df_disp['2026 Budget'] - df_disp['2025 Actuals']
        df_disp['Increase_Pct'] = (df_disp['Increase_Amt'] / df_disp['2025 Actuals'].replace(0, 1)) * 100

        # --- HEADER ---
        st.title("🏝️ Oasis Condominium HOA")
        st.subheader("2026 Annual Budget Presentation")
        st.markdown(f"""
        Welcome, Homeowners. This interactive dashboard provides full transparency into our 
        financial planning for 2026. All values are currently displayed in **{currency}**.
        """)

        # --- HELP SECTION ---
        with st.expander("❓ Help: How to read this dashboard"):
            st.write("""
            - **Top 5 Drivers:** Shows the specific areas where our spending is increasing the most compared to last year's actual spending.
            - **Visual Trends:** Compare historical spending (2024/2025) against the 2026 proposal. 
            - **Hovering:** Move your mouse over any bar in the 'Trends by Area' chart to see the specific justification note from the Treasurer.
            - **Heat Map:** Any row highlighted in red indicates a budget increase over 0% for full transparency.
            """)

        # --- TOP 5 DRIVERS ---
        st.divider()
        st.header("📢 Top 5 Budget Increase Drivers")
        top_5 = df_disp.nlargest(5, 'Increase_Amt')

        cols = st.columns(5)
        for i, (idx, row) in enumerate(top_5.iterrows()):
            with cols[i]:
                st.metric(
                    label=row['Area'], 
                    value=f"{symbol[currency]}{row['2026 Budget']:,.0f}",
                    delta=f"{row['Increase_Pct']:.1f}% vs 2025"
                )
                st.caption(f"**Reason:** {row['2026 Notes']}")

        # --- VISUAL TRENDS BY CATEGORY ---
        st.divider()
        st.header("📊 Spending Trends by Category")
        cat_summary = df_disp.groupby('Category')[val_cols].sum().reset_index()
        cat_melted = cat_summary.melt(id_vars='Category', var_name='Year', value_name='Amount')

        fig_cat = px.bar(
            cat_melted, x='Category', y='Amount', color='Year',
            barmode='group',
            labels={'Amount': f'Total ({currency})'},
            title="Comparison: 2024 vs 2025 vs 2026",
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_cat, use_container_width=True)

        # --- VISUAL TRENDS BY AREA (WITH HOVER JUSTIFICATION) ---
        st.divider()
        st.header("🔍 Detailed Trends by Area")
        selected_cat = st.selectbox("Filter by Category", df_disp['Category'].unique())

        area_df = df_disp[df_disp['Category'] == selected_cat]
        area_melted = area_df.melt(
            id_vars=['Area', '2026 Notes'], 
            value_vars=val_cols, 
            var_name='Year', 
            value_name='Amount'
        )

        fig_area = px.bar(
            area_melted, x='Area', y='Amount', color='Year',
            barmode='group',
            hover_data={'2026 Notes': True, 'Amount': ':,.2f'},
            title=f"Areas within {selected_cat}",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_area.update_layout(hoverlabel=dict(bgcolor="white", font_size=12))

        st.plotly_chart(fig_area, use_container_width=True)

        # --- HEAT MAP TABLE ---
        st.divider()
        st.header("📋 Detailed Budget & Justification Table")

        def highlight_increase(s):
            return ['background-color: #ffcccc' if (isinstance(v, float) and v > 0) else '' for v in s]

        table_df = area_df[['Area', '2025 Actuals', '2026 Budget', 'Increase_Pct', '2026 Notes']]
        table_df.columns = ['Area', f'2025 Actuals ({currency})', f'2026 Budget ({currency})', 'Var %', 'Justification']

        st.dataframe(
            table_df.style.apply(highlight_increase, subset=['Var %']).format({
                f'2025 Actuals ({currency})': '{:,.2f}',
                f'2026 Budget ({currency})': '{:,.2f}',
                'Var %': '{:.1f}%'
            }),
            use_container_width=True,
            height=400
        )

        # --- EXPORT OPTIONS ---
        st.divider()
        st.subheader("📥 Download & Print")
        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            csv_data = df_disp.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Full Budget as CSV",
                data=csv_data,
                file_name='Oasis_HOA_2026_Budget_Detailed.csv',
                mime='text/csv',
            )

        with col_exp2:
            st.info("💡 **To Save as PDF:** Press **Ctrl+P** (Windows) or **Cmd+P** (Mac) on your keyboard. Ensure 'Background Graphics' is checked in your print settings for the colors to appear.")

        st.markdown("---")
        st.caption(f"Dashboard generated for Oasis HOA General Assembly. Data Current as of {datetime.now().strftime('%Y-%m-%d')}.")
