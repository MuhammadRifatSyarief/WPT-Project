import streamlit as st
import pandas as pd
import joblib
import networkx as nx
import matplotlib.pyplot as plt

st.title('Market Basket Analysis Dashboard')

# Load data
data = joblib.load(r'D:\CTEST\V0dev-Project2-Folder\V0dev-Project2-Modeling\scripts\output\mba\pkl\mba_streamlit_data.pkl')
rules = data['data']['association_rules']
cross_sell = data['data']['cross_sell_report']

st.header('Association Rules')
st.dataframe(rules)

st.header('Cross-Sell Recommendations')
st.dataframe(cross_sell)

st.header('Rules Filter')
min_confidence = st.slider('Minimum Confidence', 0.0, 1.0, 0.5)
min_lift = st.slider('Minimum Lift', 0.0, 20.0, 1.5)

filtered_rules = rules[(rules['confidence'] >= min_confidence) & (rules['lift'] >= min_lift)]
st.write(f'Found {len(filtered_rules)} rules')
st.dataframe(filtered_rules)
