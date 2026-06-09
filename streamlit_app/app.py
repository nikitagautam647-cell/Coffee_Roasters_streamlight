import os
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]
    # Ensure numeric types
    if 'transaction_qty' in df.columns:
        df['transaction_qty'] = pd.to_numeric(df['transaction_qty'], errors='coerce').fillna(0)
    if 'unit_price' in df.columns:
        df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0)
    # Prefer provided revenue column, else compute
    if 'Revenu' in df.columns:
        df['revenue'] = pd.to_numeric(df['Revenu'], errors='coerce').fillna(0)
    else:
        df['revenue'] = df.get('unit_price', 0) * df.get('transaction_qty', 0)
    # Hours column fallback
    if 'Hours' in df.columns:
        df['hour'] = pd.to_numeric(df['Hours'], errors='coerce').fillna(0).astype(int)
    else:
        # try to parse from transaction_time
        if 'transaction_time' in df.columns:
            df['hour'] = pd.to_datetime(df['transaction_time'], format='%H:%M:%S', errors='coerce').dt.hour.fillna(0).astype(int)
        else:
            df['hour'] = 0
    return df


def main():
    st.set_page_config(page_title='Coffee Roasters Dashboard', layout='wide')

    # Coffee-themed CSS
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(90deg, #4b2e2b, #6b463f 60%);
        color: #f3ebe0;
    }
    section[data-testid="stSidebar"] {
        background-color: #3e2723;
        color: #f3ebe0;
    }
    .card {
        background-color: rgba(255,255,255,0.03);
        padding: 14px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .kpi {
        font-size: 24px;
        font-weight: 700;
        color: #fff8f0;
    }
    label, .stSelectbox, .stMultiSelect, .stSlider, .stTextInput {
        color: #f3ebe0 !important;
    }
    a, .stSidebar a { color: #d7a17a !important; }
    h1.coffee-title { color: #fff8f0; font-weight:800; margin:0; }
    h3.coffee-sub { color: #d7a17a; margin-top:4px; margin-bottom:12px; }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown(
        """
        <div style='text-align:left;'>
        <h1 class='coffee-title'>☕ Afficionado Coffee Roasters — Dashboard</h1>
        <h3 class='coffee-sub'>Sales • Demand • Locations</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # locate data file relative to this script
    base = os.path.dirname(__file__)
    data_path = os.path.join(base, '..', 'Data_sheet', 'sql Afficionado Coffee Roasters.csv')

    df = load_data(data_path)

    # Sidebar controls
    st.sidebar.header('Filters')
    stores = sorted(df['store_location'].unique()) if 'store_location' in df.columns else []
    selected_stores = st.sidebar.multiselect('Store location', options=stores, default=stores)

    # Day-of-week selector (only shown if column exists)
    if 'day_of_week' in df.columns:
        days = sorted(df['day_of_week'].unique())
        selected_days = st.sidebar.multiselect('Day of week', options=days, default=days)
        df = df[df['day_of_week'].isin(selected_days)]
    else:
        selected_days = None

    # Hour range slider
    min_hour = int(df['hour'].min()) if not df['hour'].isna().all() else 0
    max_hour = int(df['hour'].max()) if not df['hour'].isna().all() else 23
    hour_range = st.sidebar.slider('Hour range', min_value=0, max_value=23, value=(min_hour, max_hour))
    df = df[(df['hour'] >= hour_range[0]) & (df['hour'] <= hour_range[1])]

    # Revenue vs quantity toggle
    metric = st.sidebar.radio('Metric', options=['Revenue', 'Quantity'])

    # Apply store filter
    if selected_stores:
        df = df[df['store_location'].isin(selected_stores)]

    # Metric column
    metric_col = 'revenue' if metric == 'Revenue' else 'transaction_qty'

    # Layout: top row overall trend + day-of-week
    col1, col2 = st.columns([2, 1])

    # Overall sales trend: aggregate by row index or hour if available
    with col1:
        st.subheader('Overall Sales Trend')
        if 'year' in df.columns and 'transaction_time' in df.columns:
            # create an ordered index to show trend by transaction_id
            if 'transaction_id' in df.columns:
                trend = df.groupby('transaction_id')[metric_col].sum().reset_index()
                fig = px.line(trend, x='transaction_id', y=metric_col, title=f'{metric} by Transaction')
            else:
                trend = df[metric_col].cumsum().reset_index()
                fig = px.line(trend, x=trend.index, y=metric_col, title=f'Cumulative {metric}')
        else:
            trend = df.groupby('hour')[metric_col].sum().reset_index().sort_values('hour')
            fig = px.line(trend, x='hour', y=metric_col, title=f'{metric} by Hour')
        st.plotly_chart(fig, use_container_width=True)

    # Day-of-week / Time bucket panel
    with col2:
        st.subheader('Day / Time Breakdown')
        if selected_days is not None:
            dow = df.groupby('day_of_week')[metric_col].sum().reset_index()
            fig2 = px.bar(dow, x='day_of_week', y=metric_col, title=f'{metric} by Day of Week')
            st.plotly_chart(fig2, use_container_width=True)
        elif 'Time Bucket' in df.columns:
            tb = df.groupby('Time Bucket')[metric_col].sum().reset_index()
            fig2 = px.bar(tb, x='Time Bucket', y=metric_col, title=f'{metric} by Time Bucket')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info('No day-of-week or time-bucket column available in dataset.')

    # Hourly demand heatmap
    st.subheader('Hourly Demand Heatmap')
    if 'store_location' in df.columns:
        pivot = df.pivot_table(values=metric_col, index='hour', columns='store_location', aggfunc='sum', fill_value=0)
        # Plot using px.imshow
        fig3 = px.imshow(pivot.T, labels=dict(x='Hour', y='Store', color=metric), x=pivot.index, y=pivot.columns)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info('Store location column not found; cannot build heatmap.')

    # Location comparison panels
    st.subheader('Location Comparison')
    if 'store_location' in df.columns:
        loc = df.groupby('store_location')[metric_col].sum().reset_index().sort_values(metric_col, ascending=False)
        fig4 = px.bar(loc, x='store_location', y=metric_col, title=f'{metric} by Store')
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info('No store_location column found for comparison.')


if __name__ == '__main__':
    main()
