import streamlit as st
from nba_boxscore_fetcher import *
import time
from streamlit.ScriptRunner import RerunException

with open('frontend/css/streamlit.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

df = get_daily_player_data()
df.style.hide_index()

df['moment'] = df['Set']+'-'+df['Tier']+'-'+df['Series']+'-'+df['Play']

fixed_categories = ['jerseyNum', 'team','minutes']
game_detail_categories = ['opp','score','game_clock']
topshot_categories = ['moment','Circulation Count','Low Ask']
stat_categories = ['points','reboundsTotal','assists','steals','blocks']

sort_by = ['points', 'minutes']
asc_list = [False, False]

columns = df.columns.sort_values().tolist()

for cat in fixed_categories:
    columns.remove(cat)

options = st.sidebar.multiselect(
     'Which Stat Categories are you interested in?',columns,stat_categories)

st.sidebar.checkbox("Click Here to Refresh")

categories = fixed_categories+options+game_detail_categories+topshot_categories

st.dataframe(df[df['status']=="ACTIVE"].sort_values(sort_by, ascending=asc_list)[categories], height=1200)
