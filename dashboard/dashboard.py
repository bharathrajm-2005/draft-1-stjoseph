import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time
import plotly.express as px

# --- Configuration ---
API_BASE_URL = "http://localhost:5000/api"

st.set_page_config(page_title="Hospital Experience Admin", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for hospital-grade UI
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff !important; padding: 20px !important; border-radius: 12px !important; border: 1px solid #e2e8f0 !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important; }
    h1, h2, h3 { color: #1e293b !important; font-family: 'Inter', sans-serif; font-weight: 600 !important; }
    .ticket-card { background-color: white; border-left: 6px solid #3b82f6; padding: 24px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: transform 0.2s; }
    .ticket-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
    .status-open { background-color: #fee2e2; color: #991b1b; padding: 4px 12px; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; }
    .status-progress { background-color: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; }
    .status-resolved { background-color: #d1fae5; color: #065f46; padding: 4px 12px; border-radius: 9999px; font-size: 0.875rem; font-weight: 600; }
    .sentiment-negative { color: #dc2626; font-weight: 700; }
    .sentiment-neutral { color: #4b5563; font-weight: 700; }
    .sentiment-positive { color: #16a34a; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def fetch_data(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", timeout=5)
        if response.status_code == 200:
            return response.json()['data']
        return []
    except Exception:
        return []

def update_status(task_id, new_status):
    try:
        res = requests.patch(f"{API_BASE_URL}/tasks/{task_id}", json={"status": new_status}, timeout=5)
        if res.status_code == 200:
            st.toast(f"Ticket #{task_id} marked as {new_status}", icon="✅")
            return True
        st.error(f"Failed to update status: {res.text}")
        return False
    except Exception as e:
        st.error(f"Error updating status: {e}")
        return False

# Sorting logic helper
def sort_tickets(df):
    if df.empty:
        return df
    
    # Define priorities
    sentiment_map = {'Negative': 0, 'Neutral': 1, 'Positive': 2}
    status_map = {'Open': 0, 'In Progress': 1, 'Resolved': 2}
    
    df['sentiment_priority'] = df['sentiment'].map(sentiment_map).fillna(3)
    df['status_priority'] = df['status'].map(status_map).fillna(3)
    
    # Sort: Status (Open > In Progress > Resolved), then Sentiment (Neg > Neu > Pos), then Date (Newest)
    return df.sort_values(
        by=['status_priority', 'sentiment_priority', 'created_at'], 
        ascending=[True, True, False]
    ).drop(columns=['sentiment_priority', 'status_priority'])

# --- Sidebar (Static Filters) ---
st.sidebar.title("⚕️ Admin Portal")
st.sidebar.subheader("Priority Management")

if 'filters_initialized' not in st.session_state:
    st.session_state.filters_initialized = True
    st.session_state.selected_depts = ["Billing", "Clinical", "Facilities", "Wait Time", "N/A"]
    st.session_state.selected_sentiments = ["Negative", "Neutral", "Positive"]
    # Default: Show only Open and In Progress
    st.session_state.selected_statuses = ["Open", "In Progress"]

st.sidebar.divider()
st.sidebar.header("Active Filters")

selected_depts = st.sidebar.multiselect("Department", ["Billing", "Clinical", "Facilities", "Wait Time", "N/A"], default=st.session_state.selected_depts)
selected_sentiments = st.sidebar.multiselect("Sentiment", ["Negative", "Neutral", "Positive"], default=st.session_state.selected_sentiments)
selected_statuses = st.sidebar.multiselect("Status", ["Open", "In Progress", "Resolved"], default=st.session_state.selected_statuses)

if st.sidebar.button("Force Global Refresh"):
    st.rerun()

# --- Main Dashboard (Fragmented for smooth refresh) ---
@st.fragment(run_every=10)
def render_live_dashboard():
    # 1. Fetch and Prepare Data
    feedbacks = fetch_data("get-feedback")
    tasks = fetch_data("tasks")
    
    if not feedbacks:
        st.info("Waiting for patient feedback data...")
        return

    df_f = pd.DataFrame(feedbacks)
    df_t = pd.DataFrame(tasks)
    
    if not df_t.empty:
        df = pd.merge(df_f, df_t, left_on='id', right_on='feedback_id', how='left', suffixes=('', '_task'))
    else:
        df = df_f.copy()
        df['status'] = 'N/A'
        df['department'] = 'N/A'
        df['id_task'] = None

    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # 2. Filter & Sort
    filtered_df = df[
        (df['department'].isin(selected_depts)) &
        (df['sentiment'].isin(selected_sentiments)) &
        (df['status'].isin(selected_statuses))
    ]
    
    sorted_df = sort_tickets(filtered_df)

    # 3. UI Header & Metrics
    st.title("Hospital Analytics & Ticket Management")
    
    m1, m2, m3, m4 = st.columns(4)
    total_active = len(df[df['status'].isin(['Open', 'In Progress'])])
    m1.metric("Active Tickets", total_active)
    
    avg_rating = df['rating'].mean() if 'rating' in df.columns else 0.0
    m2.metric("Avg Patient Rating", f"{avg_rating:.1f}/5.0")
    
    neg_count = len(df[df['sentiment'] == 'Negative'])
    m3.metric("Negative Feeback", neg_count, delta=f"{neg_count} cases", delta_color="inverse")
    
    top_dept = df[df['status'] != 'N/A']['department'].value_counts().idxmax() if not df[df['status'] != 'N/A'].empty else "N/A"
    m4.metric("Risk Area", top_dept)

    # 4. Content Tabs
    tab1, tab2 = st.tabs(["📋 Ticket Queue", "📊 Performance Analytics"])

    with tab1:
        st.subheader("Priority Management Queue")
        
        if sorted_df.empty:
            st.info("No tickets matching current filters.")
        else:
            # Focus on tickets (items with a corresponding task)
            active_tickets = sorted_df[sorted_df['id_task'].notnull()]
            
            if active_tickets.empty:
                st.success("All patient concerns have been addressed! (No active tickets found)")
            else:
                for idx, row in active_tickets.iterrows():
                    with st.container():
                        c1, c2 = st.columns([5, 1])
                        
                        with c1:
                            status_badge = f'<span class="status-{row["status"].lower().replace(" ", "")}">{row["status"]}</span>'
                            sentiment_badge = f'<span class="sentiment-{row["sentiment"].lower()}">{row["sentiment"]}</span>'
                            
                            st.markdown(f"""
                            <div class="ticket-card">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                    <h3 style="margin: 0;">Ticket #{row['id_task']} — {row['patient_id']}</h3>
                                    {status_badge}
                                </div>
                                <div style="margin-bottom: 12px;">
                                    <strong>Dept:</strong> {row['department']} &nbsp;&nbsp;|&nbsp;&nbsp; 
                                    <strong>Sentiment:</strong> {sentiment_badge}
                                </div>
                                <p style="font-size: 1.1rem; line-height: 1.5; color: #334155; border-top: 1px solid #f1f5f9; padding-top: 12px; margin-top: 8px;">
                                    <em>"{row['feedback_text']}"</em>
                                </p>
                                <div style="margin-top: 16px; font-size: 0.85rem; color: #94a3b8;">
                                    Received: {row['created_at'].strftime('%b %d, %H:%M:%S')}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with c2:
                            st.write("") # Adjust for vertical alignment
                            st.write("")
                            st.write("")
                            current_idx = ["Open", "In Progress", "Resolved"].index(row['status']) if row['status'] in ["Open", "In Progress", "Resolved"] else 0
                            new_status = st.selectbox(
                                "Action", 
                                ["Open", "In Progress", "Resolved"], 
                                index=current_idx,
                                key=f"action_{row['id_task']}"
                            )
                            if new_status != row['status']:
                                if update_status(row['id_task'], new_status):
                                    st.rerun()

    with tab2:
        st.subheader("System-wide Analytics")
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("##### Sentiment Mix")
            fig_sent = px.pie(df, names='sentiment', hole=0.5, color='sentiment',
                           color_discrete_map={'Positive':'#10b981', 'Neutral':'#64748b', 'Negative':'#ef4444'})
            st.plotly_chart(fig_sent, on_select="ignore")
            
        with col_right:
            st.markdown("##### Issue Categories")
            df_issue = df['issue_type'].value_counts().reset_index()
            df_issue.columns = ['issue_type', 'count']
            fig_cat = px.bar(df_issue, x='issue_type', y='count', color='count', 
                           color_continuous_scale='Reds', labels={'count': 'Cases'})
            st.plotly_chart(fig_cat, on_select="ignore")

        st.markdown("##### Incident Timeline")
        trend_df = df.set_index('created_at').resample('h').count().reset_index()
        fig_trend = px.line(trend_df, x='created_at', y='id', labels={'id': 'Feedback Rate'},
                          title="Feedback Inflow (Daily View)")
        st.plotly_chart(fig_trend, on_select="ignore")

    # Time-stamp for sync verification (Outside sidebar to avoid st.fragment error)
    st.divider()
    st.caption(f"Refreshed: {datetime.now().strftime('%H:%M:%S')} • Mode: High Availability Synchronous Tracking")

# Execute
render_live_dashboard()