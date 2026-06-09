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

    # KPI Cards (reflect filtered data)
    total_revenue = float(df['revenue'].sum()) if 'revenue' in df.columns else 0.0
    total_qty = int(df['transaction_qty'].sum()) if 'transaction_qty' in df.columns else 0
    avg_ticket = float(df['revenue'].sum() / df['transaction_id'].nunique()) if 'transaction_id' in df.columns and df['transaction_id'].nunique() > 0 else float(df['revenue'].mean() if not df['revenue'].empty else 0)
    top_store = df.groupby('store_location')['revenue'].sum().idxmax() if 'store_location' in df.columns else 'N/A'
    top_product = df.groupby('product_detail')['revenue'].sum().idxmax() if 'product_detail' in df.columns else 'N/A'

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"""<div class='card'>💵<br><div class='kpi'>${total_revenue:,.2f}</div><div style='opacity:0.8'>Total Revenue</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class='card'>🧾<br><div class='kpi'>{total_qty:,}</div><div style='opacity:0.8'>Total Quantity</div></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class='card'>🎟️<br><div class='kpi'>${avg_ticket:,.2f}</div><div style='opacity:0.8'>Avg Ticket</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class='card'>📍<br><div class='kpi'>{top_store}</div><div style='opacity:0.8'>Top Store by Revenue</div></div>""", unsafe_allow_html=True)

    # Tabs: Performance, Risk, Recommendation, Benefits
    tab_perf, tab_risk, tab_rec, tab_benefit = st.tabs([
        'Performance Overview', 'Risk Analysis', 'Recommendation', 'Benefits'
    ])

    # Performance Overview
    with tab_perf:
        st.subheader('Overall Sales Trend')
        if 'year' in df.columns and 'transaction_time' in df.columns and 'transaction_id' in df.columns:
            trend = df.groupby('transaction_id')[metric_col].sum().reset_index()
            fig = px.line(trend, x='transaction_id', y=metric_col, title=f'{metric} by Transaction')
        else:
            trend = df.groupby('hour')[metric_col].sum().reset_index().sort_values('hour')
            fig = px.line(trend, x='hour', y=metric_col, title=f'{metric} by Hour')
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader('Day / Time Breakdown')
            if selected_days is not None:
                dow = df.groupby('day_of_week')[metric_col].sum().reset_index()
                fig2 = px.bar(dow, x='day_of_week', y=metric_col, title=f'{metric} by Day of Week', color_discrete_sequence=['#6b4a3e'])
                st.plotly_chart(fig2, use_container_width=True)
            elif 'Time Bucket' in df.columns:
                tb = df.groupby('Time Bucket')[metric_col].sum().reset_index()
                fig2 = px.bar(tb, x='Time Bucket', y=metric_col, title=f'{metric} by Time Bucket', color_discrete_sequence=['#6b4a3e'])
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info('No day-of-week or time-bucket column available in dataset.')

        with c2:
            st.subheader('Hourly Demand Heatmap')
            if 'store_location' in df.columns:
                pivot = df.pivot_table(values=metric_col, index='hour', columns='store_location', aggfunc='sum', fill_value=0)
                fig3 = px.imshow(pivot.T, labels=dict(x='Hour', y='Store', color=metric), x=pivot.index, y=pivot.columns, color_continuous_scale='Oranges')
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info('Store location column not found; cannot build heatmap.')

    # Risk Analysis
    with tab_risk:
        st.subheader('Risk & Weaknesses')
        if df.empty:
            st.warning('No data for current filters.')
        else:
            # Low revenue stores
            if 'store_location' in df.columns:
                low_rev = df.groupby('store_location')['revenue'].sum().reset_index().sort_values('revenue').head(5)
                fig_r1 = px.bar(low_rev, x='store_location', y='revenue', title='Lowest Revenue Stores', color_discrete_sequence=['#b07c6b'])
                st.plotly_chart(fig_r1, use_container_width=True)

            # Low revenue hours
            low_hours = df.groupby('hour')['revenue'].sum().reset_index().sort_values('revenue').head(5)
            fig_r2 = px.bar(low_hours, x='hour', y='revenue', title='Lowest Revenue Hours', color_discrete_sequence=['#b07c6b'])
            st.plotly_chart(fig_r2, use_container_width=True)

            st.markdown("""
            **Quick Risk Notes:**
            - Low revenue stores: may suffer from poor location, product mix, or staffing.
            - Low revenue hours: indicates off-peak times with potential for promotions.
            """)

    # Recommendation
    with tab_rec:
        st.subheader('Recommendations (short)')
        recommendations = []
        # Recommendation based on low_rev
        if 'store_location' in df.columns:
            low_store = low_rev.iloc[0]['store_location'] if not low_rev.empty else None
            if low_store:
                recommendations.append((f'Improve performance at {low_store}',
                                        'Why: Low revenue vs peers.',
                                        'Action: Run targeted promotions, review product mix, adjust staffing.',
                                        'Benefit: Increased footfall and revenue'))

        if not low_hours.empty:
            h = int(low_hours.iloc[0]['hour'])
            recommendations.append((f'Boost {h}:00 hour',
                                    'Why: Off-peak with low sales.',
                                    'Action: Time-limited deals, bundles, or happy hour pricing.',
                                    'Benefit: Better utilization of staff and increased incremental sales'))

        if not recommendations:
            st.info('No specific recommendations for the current filters.')
        else:
            for title, why, action, benefit in recommendations:
                st.markdown(f"""
                <div class='card'>
                <b>{title}</b><br>
                <i>{why}</i><br>
                <b>What to do:</b> {action}<br>
                <b>Benefits:</b> {benefit}
                </div>
                """, unsafe_allow_html=True)

    # Benefits
    with tab_benefit:
        st.subheader('Where Profit Comes From')
        if df.empty:
            st.warning('No data to show.')
        else:
            if 'store_location' in df.columns:
                top_loc = df.groupby('store_location')['revenue'].sum().reset_index().sort_values('revenue', ascending=False).head(5)
                fig_b1 = px.bar(top_loc, x='store_location', y='revenue', title='Top Stores by Revenue', color_discrete_sequence=['#6b4a3e'])
                st.plotly_chart(fig_b1, use_container_width=True)
            if 'product_detail' in df.columns:
                top_prod = df.groupby('product_detail')['revenue'].sum().reset_index().sort_values('revenue', ascending=False).head(10)
                fig_b2 = px.bar(top_prod, x='product_detail', y='revenue', title='Top Products by Revenue', color_discrete_sequence=['#6b4a3e'])
                st.plotly_chart(fig_b2, use_container_width=True)
            st.markdown(f"""<div class='card'>Top product: <b>{top_product}</b></div>""", unsafe_allow_html=True)


if __name__ == '__main__':
    main()
