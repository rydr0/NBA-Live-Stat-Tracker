import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import streamlit as st
import numpy as np
import time
from streamlit_autorefresh import st_autorefresh
from utils import *
from nba_boxscore_fetcher import Stat_Dataset
import requests
import pandas as pd
from datetime import datetime
import pytz
import streamlit as st
import numpy as np
import time

st.sidebar.image("nba_logo.png")

count = st_autorefresh(interval=60000, limit=120, key="refreshapp")

# Custom CSS Styles and HTML
with open("frontend/css/streamlit.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Set defaults:
# ---------------------------------------------------------------------
challenge = st.sidebar.checkbox("Check here to use challenge settings", value=True)
num_highlighted = 5

# Variable columns depending on challenge
challenge_cats = ["PTS", "REB", "AST"]
if challenge:
    stat_categories = challenge_cats
else:
    stat_categories = ["PTS", "REB", "AST", "STL", "BLK", "TOV"]

# Some default columns for the dataframe
fixed_categories = ["SCORE", "GAME_STATUS", "MIN", "ONCOURT", "STARTER"]
EASY_categories = ["EASY_MOMENT", "COUNT_EASY", "LOW_ASK_EASY", "4HCHANGE_EASY"]
HARD_categories = ["HARD_MOMENT", "COUNT_HARD", "LOW_ASK_HARD", "4HCHANGE_HARD"]
topshot_categories = EASY_categories  # + HARD_categories +

# Tiebreakers for when stat of interest is tied, used in determining people with most of a stat
tiebreakers = ["DIFFERENTIAL", "PLUS_MINUS", "MIN"]

# ----------------------------------------------------------------------

# Create dataframe that webapp will be filtering
today_dataset = Stat_Dataset()
df = today_dataset.gameday_df
todays_games = today_dataset.todays_games
start_times = todays_games["START_TIME"].sort_values()

# df = df.join(todays_games,)
import_previous_days_csv = False
previous_day_csv_path = "prevgamedays/2022-01-2122_NBAStats_edited.csv"
columns = df.columns
columns = [x.upper() for x in columns]
columns.sort()
df_create_columns(df)


df["ONCOURT"] = df.apply(on_court_function, axis=1)
df["STARTER"] = df.apply(starter_function, axis=1)

columns = [x for x in columns if x + "_AVG" in columns]

# Create a multiselect option for individual categories and generate prediction for each option selected
options = st.sidebar.multiselect(
    "Which stats are you interested in?", columns, stat_categories
)

# create a multiselect option for adding multiple categories (cat1 + cat2 + cat3...)
add_categories = st.sidebar.multiselect(
    "Do you want to add up any categories?", columns,
)
add_categories = challenge_cats
add_categories_combined = "+".join(add_categories)

# create multiselect option for subtracting categories (cat1 - cat2 - cat3...)
sub_categories = st.sidebar.multiselect(
    "Do you want to subtract any categories? Categories are subtracted from the first listed",
    columns,
)
sub_categories_combined = "-".join(sub_categories)

for option in options:
    df[option + "_PROJ"] = df.apply(project_stat, stat=option, axis=1)

if add_categories or sub_categories:
    df[add_categories_combined + "_PROJ"] = 0
    df[sub_categories_combined + "_PROJ"] = 0
    for cat in add_categories:
        df[add_categories_combined + "_PROJ"] += df.apply(
            project_stat, stat=cat, axis=1
        )
    for cat in sub_categories:
        if cat == sub_categories[0]:
            df[sub_categories_combined + "_PROJ"] = df.apply(
                project_stat, stat=cat, axis=1
            )
        else:
            df[sub_categories_combined + "_PROJ"] -= df.apply(
                project_stat, stat=cat, axis=1
            )

if add_categories_combined == "" and sub_categories_combined == "":
    options_proj = [x + "_PROJ" for x in options]
elif add_categories_combined == "":
    options_proj = [x + "_PROJ" for x in options] + [sub_categories_combined + "_PROJ"]
elif sub_categories_combined == "":
    options_proj = [x + "_PROJ" for x in options] + [add_categories_combined + "_PROJ"]
else:
    options_proj = [x + "_PROJ" for x in options] + [
        add_categories_combined + "_PROJ",
        sub_categories_combined + "_PROJ",
    ]

active_only = df["STATUS"] == "ACTIVE"
df_for_saving = df[active_only].copy().astype(str)

if import_previous_days_csv == True:
    df_previous = pd.read_csv(previous_day_csv_path, dtype=df.dtypes.to_dict())
    df_previous.fillna(0, inplace=True)
    df_previous.set_index(["NAME", "TEAM"], inplace=True)
    df = pd.concat([df, df_previous])

change_4h_percentage(df)

# Generate Multiple categories stats depending on if addition or subtractiong
if add_categories:
    df[add_categories_combined] = 0

    for cat in add_categories:
        df[add_categories_combined] += df[cat]

if sub_categories:
    df[sub_categories_combined] = df[sub_categories[0]]

    for cat in sub_categories:
        if cat != sub_categories[0]:
            df[sub_categories_combined] -= df[cat]

# Deal with different cases of Multiple categories being chosen
# --------------------------------------------------------------

# Multiple categories selected for adding and subtracting
if add_categories and sub_categories:
    categories = (
        fixed_categories
        + [add_categories_combined, sub_categories_combined]
        + options
        + options_proj
        + [x for x in tiebreakers if x != "MIN"]
        + topshot_categories
    )
    default_sort = add_categories_combined

# Multiple categories selected for adding
elif add_categories:
    categories = (
        fixed_categories
        + [add_categories_combined]
        + options
        + options_proj
        + [x for x in tiebreakers if x != "MIN"]
        + topshot_categories
    )
    default_sort = add_categories_combined

# Multiple categories selected only for subtracting
elif sub_categories:
    categories = (
        fixed_categories
        + [sub_categories_combined]
        + options
        + options_proj
        + [x for x in tiebreakers if x != "MIN"]
        + topshot_categories
    )
    default_sort = sub_categories_combined

# Multiple categories not selected
else:
    categories = (
        fixed_categories
        + options
        + options_proj
        + [x for x in tiebreakers if x != "MIN"]
        + topshot_categories
    )
    default_sort = options[0]

sort_columns = columns + [add_categories_combined, sub_categories_combined]

how_many = st.sidebar.slider(
    "Highlight the top ____ players in sorted category",
    min_value=0,
    max_value=df.shape[0],
    value=num_highlighted,
    step=1,
)

sort_by = st.sidebar.selectbox(
    "Which category do you want to sort by?",
    options + ["PTS+REB+AST"],
    (options + ["PTS+REB+AST"]).index(default_sort),
)

# Button to refresh live data
st.sidebar.button("Click Here to Refresh Live Data")
bench_index = (df["STARTER"] != "Starter") & (df["STATUS"] != "INACTIVE")

list_top = get_top_stats(df[bench_index], how_many, sort_by, tiebreakers)

if start_times[0] < today_dataset.now:
    sort_by = [sort_by] + tiebreakers
else:
    sort_by = [sort_by] + tiebreakers + [sort_by + "_PROJ"]
asc_list = [0] * len(sort_by)


st.title("NBA Stat Tracker for {}".format(today_dataset.game_date))
# todays_games["Start Time"] = todays_games["Start Time"].dt.strftime(("%r EST"))
# todays_games.set_index("Start Time", inplace=True)

st.table(
    todays_games.reset_index()[
        ["GAME_STATUS", "AWAY_TEAM", "AWAY_SCORE", "HOME_TEAM", "HOME_SCORE",]
    ]
)

df = df.sort_values(sort_by, ascending=asc_list)[categories]
df.fillna("-", inplace=True)

dfStyler = df.style.set_properties(**{"text-align": "center"})
dfStyler.set_table_styles([dict(selector="th", props=[("text-align", "center")])])

# Options for Pandas DataFrame Style
if count % 1 == 0 or count == 0:
    # if datetime.now > today_dataset.start_times[-1] + timedelta(hours=3):
    df_for_saving.to_csv(
        path_or_buf="prevgamedays/" + datetime.now().strftime("%F") + "_NBAStats.csv"
    )
    if start_times[0] < today_dataset.now:
        if how_many == 0:
            st.dataframe(df[bench_index], height=700)
        else:
            st.dataframe(
                df[bench_index].style.apply(bg_color, list_top=list_top), height=700
            )
    else:
        st.dataframe(df[bench_index], height=700)

