import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Setup & Data Loading
st.set_page_config(page_title="Oasis HOA 2026 Budget Review", layout="wide")
df = pd.read_csv('Oasis HOA Yearly Budget - Compare.csv')

# 2. Currency Logic
rates = {"MXN": 1.0, "USD": 0.058, "CAD": 0.079}
st.sidebar.header("Settings")
currency = st.sidebar.selectbox("Select Currency", ["MXN", "USD", "CAD"])
rate = rates[currency]

# Apply conversion
df['2025_Actual_Conv'] = df['2025 Actuals'] * rate
df['2026_Budget_Conv'] = df['2026 Budget'] * rate
df['Diff'] = df['2026_Budget_Conv'] - df['2025_Actual_Conv']
df['% Change'] = (df['Diff'] / df['2025_Actual_Conv']) * 100

# 3. Header Section
st.title("🏝️ Oasis Condominium: 2026 Operational Budget")
st.info(f"Comparison: 2026 Proposed Budget vs. 2025 Actual Expenses. All values in {currency}.")

# 4. Top 3 Drivers Section (Dynamic)
st.subheader("🚀 Key Budget Drivers")
top_3 = df.nlargest(3, 'Diff')
cols = st.columns(3)
for i, (index, row) in enumerate(top_3.iterrows()):
    cols[i].metric(label=row['Item'], value=f"{row['2026_Budget_Conv']:,.2f}", delta=f"{row['% Change']:.1f}%")
    cols[i].caption(f"Justification: {row['Justification']}")

# 5. Visual Trends
st.write("---")
fig = px.bar(df, x='Category', y=['2025_Actual_Conv', '2026_Budget_Conv'], 
             barmode='group', title="Spend Comparison by Category",
             hover_data={'Justification': True}, 
             labels={'value': f'Amount ({currency})', 'variable': 'Year'})
st.plotly_chart(fig, use_container_width=True)

# 6. Detailed Data Table with Color Coding
def highlight_increase(val):
    color = 'red' if val > 0 else 'green'
    return f'color: {color}'

st.subheader("Detailed Breakdown")
st.dataframe(df[['Category', 'Item', '2025_Actual_Conv', '2026_Budget_Conv', '% Change', 'Justification']]
             .style.map(highlight_increase, subset=['% Change'])
             .format(precision=2))

# 7. Download Button
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Summary for Meeting", data=csv, file_name="Oasis_2026_Budget_Summary.csv")
