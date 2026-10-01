import streamlit as st
import textwrap

st.markdown("""
    <div style="color:red;">HTML TEST 1 (Indented)</div>
""", unsafe_allow_html=True)

st.markdown(textwrap.dedent("""
    <div style="color:red;">HTML TEST 2 (Dented)</div>
"""), unsafe_allow_html=True)
