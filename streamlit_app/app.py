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

    # Coffee-themed CSS (lighter coffee + off-white accents)
    st.markdown("""
    <style>
    .stApp {
        /* lighter coffee-brown gradient */
        background: linear-gradient(90deg, #e6d4c6 0%, #d7bfa8 60%);
        color: #2f1e1b;
    }
    section[data-testid="stSidebar"] {
        background-color: #8b6b5a;
        color: #efe9e1;
    }
    .card {
        background-color: rgba(255,255,255,0.9);
        padding: 14px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid rgba(47,30,27,0.06);
        color: #2f1e1b;
    }
    .kpi {
        font-size: 24px;
        font-weight: 700;
        color: #2f1e1b;
    }
    label, .stSelectbox, .stMultiSelect, .stSlider, .stTextInput {
        color: #efe9e1 !important;
    }
    a, .stSidebar a { color: #6b4226 !important; }
    h1.coffee-title { color: #2f1e1b; font-weight:800; margin:0; }
    h3.coffee-sub { color: #6b4226; margin-top:4px; margin-bottom:12px; }
    /* Tabs text color */
    button[data-baseweb="tab"] { color: #ffffff !important; }
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

    # Product category filter
    product_cats = sorted(df['product_category'].unique()) if 'product_category' in df.columns else []
    selected_categories = st.sidebar.multiselect('Product Category', options=product_cats, default=product_cats)

    # Transaction time filter (start/end)
    if 'transaction_time' in df.columns:
        df['transaction_time_dt'] = pd.to_datetime(df['transaction_time'], format='%H:%M:%S', errors='coerce')
        if not df['transaction_time_dt'].isna().all():
            min_t = df['transaction_time_dt'].min().time()
            max_t = df['transaction_time_dt'].max().time()
            t_start = st.sidebar.time_input('Start time', value=min_t)
            t_end = st.sidebar.time_input('End time', value=max_t)
        else:
            t_start = t_end = None
    else:
        t_start = t_end = None

    # Day-of-week selector (only shown if column exists)
    if 'day_of_week' in df.columns:
        days = sorted(df['day_of_week'].unique())
        selected_days = st.sidebar.multiselect('Day of week', options=days, default=days)
        df = df[df['day_of_week'].isin(selected_days)]
    else:
        selected_days = None

    # Apply product category filter
    if selected_categories:
        df = df[df['product_category'].isin(selected_categories)]

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

    # Apply transaction time filter
    if t_start and t_end and 'transaction_time_dt' in df.columns:
        df = df[(df['transaction_time_dt'].dt.time >= t_start) & (df['transaction_time_dt'].dt.time <= t_end)]

    # Metric column
    metric_col = 'revenue' if metric == 'Revenue' else 'transaction_qty'

    # KPI Cards (reflect filtered data)
    total_revenue = float(df['revenue'].sum()) if 'revenue' in df.columns else 0.0
    total_qty = int(df['transaction_qty'].sum()) if 'transaction_qty' in df.columns else 0
    avg_ticket = float(df['revenue'].sum() / df['transaction_id'].nunique()) if 'transaction_id' in df.columns and df['transaction_id'].nunique() > 0 else float(df['revenue'].mean() if not df['revenue'].empty else 0)
    top_store = df.groupby('store_location')['revenue'].sum().idxmax() if 'store_location' in df.columns else 'N/A'
    top_product = df.groupby('product_detail')['revenue'].sum().idxmax() if 'product_detail' in df.columns else 'N/A'

    # Precompute low revenue stores/hours for risk & recommendation
    low_rev = df.groupby('store_location')['revenue'].sum().reset_index().sort_values('revenue') if 'store_location' in df.columns else pd.DataFrame()
    low_hours = df.groupby('hour')['revenue'].sum().reset_index().sort_values('revenue') if 'hour' in df.columns else pd.DataFrame()

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"""<div class='card'>💵<br><div class='kpi'>${total_revenue:,.2f}</div><div style='opacity:0.8'>Total Revenue</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class='card'>🧾<br><div class='kpi'>{total_qty:,}</div><div style='opacity:0.8'>Total Quantity</div></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class='card'>🎟️<br><div class='kpi'>${avg_ticket:,.2f}</div><div style='opacity:0.8'>Avg Ticket</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class='card'>📍<br><div class='kpi'>{top_store}</div><div style='opacity:0.8'>Top Store by Revenue</div></div>""", unsafe_allow_html=True)

    # Tabs: Performance, Risk, Profit Sources (Benefits), Use Recommendation, Recommendation (detailed)
    tab_perf, tab_risk, tab_benefit, tab_use_rec, tab_rec = st.tabs([
        'Performance Overview', 'Risk Analysis', 'Profit Sources', 'Use Recommendation', 'Recommendation'
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

    # Use Recommendation (how to apply recommendations)
    with tab_use_rec:
        st.subheader('How to Use Recommendations')
        st.markdown("""
        - Review recommended store or hour actions and A/B test promotions for one week.
        - Track incremental revenue vs control group and adjust offers.
        - Prioritize high-margin products and measure lift in average ticket.
        - Use scheduling to shift staff to peak hours and test limited-time bundles during low hours.
        """)

    # Recommendation (detailed, placed last)
    with tab_rec:
        st.subheader('Recommendations (detailed)')
        if df.empty:
            st.info('No recommendations for empty dataset.')
        else:
            recs = []
            if not low_rev.empty:
                low_store_name = low_rev.iloc[0]['store_location']
                recs.append({
                    'title': f'Improve {low_store_name}',
                    'why': 'Store shows lowest revenue among locations for selected filters.',
                    'what': 'Run targeted promotions, review top-selling products, audit staffing and opening hours, and local marketing.',
                    'benefit': 'Higher footfall, improved conversion, and increased revenue.'
                })
            if not low_hours.empty:
                hval = int(low_hours.iloc[0]['hour'])
                recs.append({
                    'title': f'Campaign for {hval}:00 hour',
                    'why': 'This hour has low sales indicating unused capacity.',
                    'what': 'Introduce time-bound discounts, combo offers, or loyalty points to boost visits.',
                    'benefit': 'Better staff utilization and incremental sales during off-peak.'
                })

            if not recs:
                st.info('No specific recommendations generated for current filters.')
            else:
                for r in recs:
                    st.markdown(f"""
                    <div class='card'>
                    <b>{r['title']}</b><br>
                    <b>Why:</b> {r['why']}<br>
                    <b>What to do:</b> {r['what']}<br>
                    <b>Benefits:</b> {r['benefit']}
                    </div>
                    """, unsafe_allow_html=True)

    # Profit Sources (previous Benefits)
    with tab_benefit:
        st.subheader('Profit Sources')
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
