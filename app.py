import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Setup
st.set_page_config(page_title="Oasis HOA 2026 Budget Review", layout="wide")

# 2. Data Loading & Robust Cleaning
@st.cache_data
def load_data():
    # Load the specific comparison file
    df = pd.read_csv('Oasis HOA Yearly Budget - Compare.csv')
    
    # Define columns to clean based on your CSV headers
    cols_to_fix = ['2025 Actual Expenses', '2026 Budget']
    
    for col in cols_to_fix:
        # 1. Convert to string to handle mixed types
        df[col] = df[col].astype(str)
        # 2. Remove $, commas, spaces, and handle the "-" dash as 0
        df[col] = df[col].str.replace(r'[\$, ]', '', regex=True).replace('-', '0')
        # 3. Convert to numeric, turning any remaining errors into NaN then 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

try:
    df = load_data()

    # 3. Currency Conversion Logic
    rates = {"MXN": 1.0, "USD": 0.058, "CAD": 0.079}
    st.sidebar.header("Presentation Settings")
    currency = st.sidebar.selectbox("Select Currency View", ["MXN", "USD", "CAD"])
    rate = rates[currency]

    # Calculations
    df['2025_Actual_Conv'] = df['2025 Actual Expenses'] * rate
    df['2026_Budget_Conv'] = df['2026 Budget'] * rate
    df['Diff'] = df['2026_Budget_Conv'] - df['2025_Actual_Conv']
    # Prevent division by zero for % change
    df['% Change'] = df.apply(lambda x: (x['Diff'] / x['2025_Actual_Conv'] * 100) if x['2025_Actual_Conv'] != 0 else 0, axis=1)

    # 4. Header
    st.title("🏝️ Oasis Condominium: 2026 Operational Budget")
    st.info(f"Comparing Proposed 2026 Budget vs. 2025 Actual Expenses. Currency: **{currency}**")

    # 5. Top 3 Drivers Section
    st.subheader("🚀 Top 3 Budget Increases")
    top_3 = df.nlargest(3, 'Diff')
    cols = st.columns(3)
    for i, (index, row) in enumerate(top_3.iterrows()):
        with cols[i]:
            st.metric(label=row['Area'], 
                      value=f"{row['2026_Budget_Conv']:,.2f}", 
                      delta=f"{row['% Change']:.1f}%")
            st.caption(f"**Note:** {row['2026 Notes']}")

    # 6. Visual Comparison
    st.write("---")
    cat_df = df.groupby('Category')[['2025_Actual_Conv', '2026_Budget_Conv']].sum().reset_index()
    fig = px.bar(cat_df, x='Category', y=['2025_Actual_Conv', '2026_Budget_Conv'],
                 barmode='group',
                 title="Spending Trends by Category",
                 labels={'value': f'Total ({currency})', 'variable': 'Year'},
                 color_discrete_map={'2025_Actual_Conv': '#1f77b4', '2026_Budget_Conv': '#d62728'}) # 2026 is Red
    st.plotly_chart(fig, use_container_width=True)

    # 7. Detailed Table
    st.subheader("Full Budget Breakdown")
    def color_red(val):
        return 'color: red' if isinstance(val, (int, float)) and val > 0 else 'color: black'

    display_df = df[['Category', 'Area', '2025_Actual_Conv', '2026_Budget_Conv', '% Change', '2026 Notes']].copy()
    display_df.columns = ['Category', 'Item', '2025 Actual', '2026 Budget', '% Change', 'Justification']

    st.dataframe(display_df.style.map(color_red, subset=['% Change'])
                 .format({'2025 Actual': '{:,.2f}', '2026 Budget': '{:,.2f}', '% Change': '{:,.1f}%'}))

    # 8. Download
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Summary PDF/CSV", data=csv, file_name="Oasis_2026_Budget.csv")

except Exception as e:
    st.error(f"Data Loading Error: {e}")
    st.write("Please check that your CSV column names match the expected format.")
