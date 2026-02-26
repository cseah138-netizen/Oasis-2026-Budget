import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Oasis HOA 2026 Budget", layout="wide")

# Custom CSS to improve table legibility and print layout
st.markdown("""
<style>
    .stDataFrame { font-size: 14px; }
    [data-testid="stMetricDelta"] svg { display: none; }
    /* Make metrics and dropdowns look clean */
    .stExpander { border: none !important; box-shadow: none !important; }
</style>
""", unsafe_allow_html=True)

# --- PASSWORD PROTECTION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Oasis2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Please enter the Homeowner Access Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Please enter the Homeowner Access Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    return True

if check_password():
    # --- DATA LOADING ---
    @st.cache_data
    def load_data():
        try:
            df = pd.read_csv('Oasis HOA Yearly Budget and Actuals.csv')
            cols = ['2026 Budget', '2025 Actuals', '2024 Actuals']
            for col in cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df['2026 Notes'] = df['2026 Notes'].fillna("No justification provided.")
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()

    raw_df = load_data()

    if not raw_df.empty:
        # --- CURRENCY SETTINGS ---
        st.sidebar.header("Settings")
        currency = st.sidebar.selectbox("Select Currency", ["MXN", "USD", "CAD"])
        rates = {"MXN": 1.0, "USD": 0.058, "CAD": 0.079}
        symbol = {"MXN": "MX$", "USD": "US$", "CAD": "CA$"}

        def convert(val):
            return val * rates[currency]

        # Global Color Mapping
        color_map = {
            '2024 Actuals': '#3B82F6', # Blue
            '2025 Actuals': '#22C55E', # Green
            '2026 Budget': '#EF4444'   # Red
        }

        # Apply conversion to a working dataframe
        df = raw_df.copy()
        
        # --- RE-MAPPING LOGIC FOR DRIVERS ---
        # Requirement: Combine 2025 actuals if budget was moved between areas
        # We look for "See line X" or "Already in Line X" in 2026 notes
        adj_df = df.copy()
        for idx, row in adj_df.iterrows():
            note = str(row['2026 Notes'])
            match = re.search(r'(?:See line|Already in Line)\s+(\d+)', note, re.IGNORECASE)
            if match:
                target_line = int(match.group(1))
                # Find the target row by the 'Line' column
                target_idx = adj_df[adj_df['Line'] == target_line].index
                if not target_idx.empty:
                    # Add current 2025 actuals to the target's 2025 actuals for driver calc purposes
                    adj_df.at[target_idx[0], '2025 Actuals'] += row['2025 Actuals']
                    # Zero out the current one so it doesn't show as a massive decrease/increase incorrectly
                    adj_df.at[idx, '2025 Actuals'] = 0

        # Calculate variance on adjusted data
        adj_df['Diff'] = adj_df['2026 Budget'] - adj_df['2025 Actuals']
        
        # Now convert all display values in the primary df
        val_cols = ['2024 Actuals', '2025 Actuals', '2026 Budget']
        for col in val_cols:
            df[col] = df[col].apply(convert)

        # Variance for the table (standard calculation)
        df['Increase_Amt'] = df['2026 Budget'] - df['2025 Actuals']
        df['Var %'] = df.apply(lambda row: 100.0 if (row['2025 Actuals'] == 0 and row['2026 Budget'] > 0) 
                              else (row['Increase_Amt'] / row['2025 Actuals'] * 100 if row['2025 Actuals'] != 0 else 0), axis=1)

        # --- HEADER ---
        st.title("🏝️ Oasis Condominium HOA")
        st.subheader("2026 Annual Budget Presentation")

        # --- HELP SECTION ---
        with st.expander("❓ Help: How to read this dashboard"):
            st.markdown(f"""
            - **Top 5 Drivers:** Specific areas where the 2026 budget is increasing or decreasing compared to last year's actual spending.
            - **Spending & Detailed Trends:** Compare historical spending actuals (2024/2025) against the 2026 proposed budget. In the chart legend, click the colors to turn them ON or OFF.
            - **Hovering:** Move your mouse over any bar in the 'Trends by Area' chart to see the specific justification note from the HOA.
            - **Detailed Data Table:** Any row highlighted in red indicates a budget increase of over 0%. Double click a Justification cell to see all the text in the cell.
            """)

        # --- RESERVE FUND SECTION ---
        st.divider()
        st.header("📈 Reserve Fund Accumulation")
        reserve_data = df[df['Category'].str.contains('Reserve', case=False, na=False)].sum(numeric_only=True)
        
        fig_reserve = go.Figure()
        y_axis = ["Reserve Fund Collection"]
        fig_reserve.add_trace(go.Bar(y=y_axis, x=[reserve_data['2024 Actuals']], name='2024 Actuals', orientation='h', marker_color=color_map['2024 Actuals']))
        fig_reserve.add_trace(go.Bar(y=y_axis, x=[reserve_data['2025 Actuals']], name='2025 Actuals', orientation='h', marker_color=color_map['2025 Actuals']))
        fig_reserve.add_trace(go.Bar(y=y_axis, x=[reserve_data['2026 Budget']], name='2026 Budget', orientation='h', marker_color=color_map['2026 Budget']))
        
        # Height reduced by half (from 200 to 100)
        fig_reserve.update_layout(barmode='stack', height=120, margin=dict(l=20, r=20, t=10, b=10),
                                  xaxis_title=f"Total Collected ({symbol[currency]})", showlegend=True)
        st.plotly_chart(fig_reserve, use_container_width=True)

        # Filter out Reserve Fund for analysis
        main_df = df[~df['Category'].str.contains('Reserve', case=False, na=False)].copy()
        main_adj_df = adj_df[~adj_df['Category'].str.contains('Reserve', case=False, na=False)].copy()

        # --- DRIVERS (INCREASE & DECREASE) ---
        st.divider()
        st.header("📢 Budget Drivers (vs 2025 Actuals)")
        
        inc_col, dec_col = st.columns(2)
        with inc_col:
            st.subheader("Top 5 Increases")
            top_inc = main_adj_df.nlargest(5, 'Diff')
            for _, row in top_inc.iterrows():
                # Display converted amounts
                diff_val = convert(row['Diff'])
                # Cleaning justification for display
                clean_note = str(row['2026 Notes']).replace("¨", "").replace("¨", "")
                with st.expander(f"**{row['Category']} - {row['Area']}**: +{symbol[currency]}{diff_val:,.0f}"):
                    st.write(f"**Justification:** {clean_note}")
        
        with dec_col:
            st.subheader("Top 5 Decreases")
            top_dec = main_adj_df.nsmallest(5, 'Diff')
            for _, row in top_dec.iterrows():
                diff_val = convert(row['Diff'])
                # Cleaning justification
                clean_note = str(row['2026 Notes']).replace("¨", "").replace("¨", "")
                with st.expander(f"**{row['Category']} - {row['Area']}**: {symbol[currency]}{diff_val:,.0f}"):
                    st.write(f"**Justification:** {clean_note}")

        # --- VISUAL TRENDS BY CATEGORY ---
        st.divider()
        st.header("📊 Spending Trends by Category")
        cat_summary = main_df.groupby('Category')[val_cols].sum().reset_index()
        cat_melted = cat_summary.melt(id_vars='Category', var_name='Year', value_name='Amount')

        fig_cat = px.bar(
            cat_melted, x='Category', y='Amount', color='Year',
            barmode='group',
            labels={'Amount': f'Total ({currency})'},
            color_discrete_map=color_map,
            title="Category Totals (Excludes Reserve Fund)"
        )
        st.plotly_chart(fig_cat, use_container_width=True)

        # --- DETAILED TRENDS BY AREA ---
        st.divider()
        st.header("🔍 Detailed Trends by Area")
        # Order Categories Alphabetically for consistent dropdown menu
        dropdown_options = sorted(main_df['Category'].unique())
        selected_cat = st.selectbox("Filter by Category", dropdown_options)
        
        # Fixed maximum: 2.5M MXN converted to selected currency
        max_y = convert(2500000)

        area_df = main_df[main_df['Category'] == selected_cat]
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
            color_discrete_map=color_map,
            title=f"Detailed view: {selected_cat} (Fixed Scale)",
            height=800 # Double the height for better hover experience
        )
        fig_area.update_yaxes(range=[0, max_y]) 
        st.plotly_chart(fig_area, use_container_width=True)

        # --- HEAT MAP TABLE ---
        st.divider()
        st.header("📋 Detailed Budget & Justification Table")

        def highlight_increase(s):
            return ['background-color: #ffcccc' if (isinstance(v, float) and v > 0) else '' for v in s]

        # Use the 'Line' column for indexing, format to one decimal place
        table_df = area_df[['Line', 'Area', '2025 Actuals', '2026 Budget', 'Var %', '2026 Notes']].copy()
        # Ensure 'Line' is float for one decimal place formatting
        table_df['Line'] = table_df['Line'].astype(float)
        table_df.columns = ['Line #', 'Area', f'2025 Actuals ({symbol[currency]})', f'2026 Budget ({symbol[currency]})', 'Var %', 'Justification']

        st.dataframe(
            table_df.style.apply(highlight_increase, subset=['Var %']).format({
                'Line #': '{:.1f}',
                f'2025 Actuals ({symbol[currency]})': '{:,.2f}',
                f'2026 Budget ({symbol[currency]})': '{:,.2f}',
                'Var %': '{:.1f}%'
            }).hide(axis='index'), # Hide the default 0-based dataframe index
            use_container_width=True,
            height=500
        )

        # --- DOWNLOAD ---
        st.divider()
        st.subheader("📥 Download")
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Full Data as CSV",
            data=csv_data,
            file_name=f'Oasis_HOA_2026_Budget_{currency}.csv',
            mime='text/csv',
        )

        st.markdown("---")
        st.caption(f"Oasis HOA Treasurer Tool • {datetime.now().strftime('%Y-%m-%d')}")
