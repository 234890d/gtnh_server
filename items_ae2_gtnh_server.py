import streamlit as st
from streamlit_autorefresh import st_autorefresh
from st_supabase_connection import SupabaseConnection
import plotly.express as px
import pandas as pd
import datetime
import pytz

st.set_page_config(
    page_title='GTNH - Items Tracker',
    layout='wide'
)
st.title("GTNH - Applied Energistics Items Track")

# Refresh the page every 15 minutes (900,000 milliseconds)
st_autorefresh(interval=900000, key="refresh_page")

# Supabase Table
supabase_table = "Items"

# Initialize connection
conn = st.connection("supabase", type=SupabaseConnection)

# Filter last items from the last 4 days
filter_dt = datetime.datetime.today() - datetime.timedelta(days=4)
filter_str = filter_dt.isoformat()

@st.cache_data(ttl='20m')
def get_items(table_name, since):
    result = conn.table(table_name).select("item").filter("datetime", "gt", since).execute()
    return result.data

@st.cache_data(ttl='20m')
def get_all_rows(table_name, since):
    result = conn.table(table_name).select("*").filter("datetime", "gt", since).execute()
    return result.data

# Get the list of items
items_data = get_items(supabase_table, filter_str)
items = pd.DataFrame.from_dict(items_data)
distinct_items = items["item"].unique()

# Select Box to filter an item
items_filter = st.selectbox("Select the Item", distinct_items)

# Get all rows
rows_data = get_all_rows(supabase_table, filter_str)
sort_table = pd.DataFrame.from_dict(rows_data).sort_values('datetime')

# Chart for Item
fig_col1, fig_col2 = st.columns([0.2, 0.8])

with fig_col1:
    st.markdown("### " + items_filter)
    st.markdown("#### Past 24-hour metrics")

    item_track = sort_table.loc[sort_table['item'] == items_filter].copy()
    item_track['datetime'] = pd.to_datetime(item_track["datetime"])

    now = pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None)
    last_24h = item_track[item_track["datetime"] >= now - pd.Timedelta(days=1)]

    if len(last_24h) <= 1:
        kpi_avg = 0
        kpi_change = 0
    else:
        last_24h = last_24h.copy()
        last_24h["real_production"] = last_24h["quantity"].diff().fillna(0)
        total_production = last_24h["real_production"].sum()
        total_hours = (last_24h["datetime"].max() - last_24h["datetime"].min()).total_seconds() / 3600
        kpi_avg = int(round(total_production / total_hours, 0)) if total_hours > 0 else 0
        kpi_change = int(round(total_production, 0))

    st.metric(label="Average Produced per Hour", value="{:,}".format(kpi_avg))
    st.metric(label="Total Amount Produced", value="{:,}".format(kpi_change))

with fig_col2:
    fig1 = px.line(item_track, x='datetime', y='quantity', title='Quantity of: ' + items_filter)
    st.plotly_chart(fig1, key='fig1')

# Expander with all items
with st.expander("All items:"):
    for col in distinct_items:
        temp_df = sort_table.loc[sort_table['item'] == col]
        fig = px.line(temp_df, x='datetime', y='quantity', title='Quantity of: ' + col)
        st.plotly_chart(fig)
