import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Setup
st.set_page_config(page_title="Oasis HOA 2026 Budget Review", layout="wide")

# 2. Data Loading & Cleaning
@st.cache_data
def load_data():
    df = pd.read_csv('Oasis HOA Yearly Budget - Compare.csv')
    
    # Clean currency strings (removes $, commas, and whitespace)
    cols_to_fix = ['2025 Actual Expenses', '2026 Budget']
    for col in cols_to_fix:
        df[col] = df[col].replace(r'[\$, ]', '', regex=True).astype(float)
    
    return df

df = load_data()

# 3. Currency Conversion Logic (Live Estimates)
rates = {"MXN": 1.0, "USD": 0.058, "CAD": 0.079}
st.sidebar.header("Presentation Settings")
currency = st.sidebar.selectbox("Select Currency View", ["MXN", "USD", "CAD"])
rate = rates[currency]

# Apply conversion to create display columns
df['2025_Actual_Conv'] = df['2025 Actual Expenses'] * rate
df['2026_Budget_Conv'] = df['2026 Budget'] * rate
df['Diff'] = df['2026_Budget_Conv'] - df['2025_Actual_Conv']
df['% Change'] = (df['Diff'] / df['2025_Actual_Conv'].replace(0, 1)) * 100

# 4. Header
st.title("🏝️ Oasis Condominium: 2026 Operational Budget")
st.markdown(f"**TREASURER'S REPORT:** Comparing Proposed 2026 Budget vs. 2025 Actual Spend.")
st.info(f"All values currently displayed in **{currency}**")

# 5. Top 3 Drivers Section
st.subheader("🚀 Top 3 Budget Drivers")
# Find top 3 increases by absolute dollar amount
top_3 = df.nlargest(3, 'Diff')
cols = st.columns(3)

for i, (index, row) in enumerate(top_3.iterrows()):
    with cols[i]:
        st.metric(label=row['Area'], 
                  value=f"{row['2026_Budget_Conv']:,.2f} {currency}", 
                  delta=f"{row['% Change']:.1f}% increase")
        st.caption(f"**Justification:** {row['2026 Notes']}")

# 6. Visual Comparison
st.write("---")
st.subheader("Spend Analysis by Category")
# Aggregate by category for the chart
cat_df = df.groupby('Category')[['2025_Actual_Conv', '2026_Budget_Conv']].sum().reset_index()

fig = px.bar(cat_df, x='Category', y=['2025_Actual_Conv', '2026_Budget_Conv'],
             barmode='group',
             labels={'value': f'Total Amount ({currency})', 'variable': 'Period'},
             color_discrete_map={'2025_Actual_Conv': '#636EFA', '2026_Budget_Conv': '#EF553B'})

fig.update_layout(legend_title_text='Legend')
st.plotly_chart(fig, use_container_width=True)

# 7. Detailed Table
st.subheader("Full Itemized Breakdown")
st.write("Increases are highlighted in red to guide review.")

def color_negative_red(val):
    color = 'red' if val > 0 else 'black'
    return f'color: {color}'

display_df = df[['Category', 'Area', '2025_Actual_Conv', '2026_Budget_Conv', '% Change', '2026 Notes']].copy()
display_df.columns = ['Category', 'Item', f'2025 Actual ({currency})', f'2026 Budget ({currency})', '% Change', 'Justification']

st.dataframe(display_df.style.map(color_negative_red, subset=['% Change'])
             .format({f'2025 Actual ({currency})': '{:,.2f}', f'2026 Budget ({currency})': '{:,.2f}', '% Change': '{:,.1f}%'}))

# 8. Download
csv = display_df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Summary for Physical Meeting", data=csv, file_name="Oasis_2026_Budget_Summary.csv")
