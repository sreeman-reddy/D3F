import os
import av
import pandas as pd
import threading
import streamlit as st
import datetime
#import streamlit_nested_layout
import pymysql
from streamlit_webrtc import VideoHTMLAttributes, webrtc_streamer
from pymysql.cursors import DictCursor
from audio_handling import AudioFrameHandler
from drowsy_detection import VideoFrameHandler
import plotly.express as px
import plotly.graph_objects as go

# Add your database credentials here
db_credentials = {
    "host": "localhost",
    "user": "root",
    "password": "mysql",
    "database": "d3f",
}

thresholds = {
        "EAR_THRESH": 0.18,
        "MAR_THRESH": 1.00,
        "WAIT_TIME": 4.0
    }

def get_table_names():
    connection = pymysql.connect(**db_credentials, cursorclass=DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = f"""
            SELECT table_name FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE' AND table_schema='{db_credentials['database']}' 
            ORDER BY table_name desc;
            """
            cursor.execute(sql)
            tables = [row["TABLE_NAME"] for row in cursor.fetchall()]
    finally:
        connection.close()

    formatted_tables = []
    for table in tables:
        year = table[5:9]
        month = table[9:11]
        day = table[11:13]
        hour = table[13:15]
        minute = table[15:17]
        second = table[17:19]
        formatted_table = f"Trip {month}/{day}/{year} {hour}:{minute}:{second}"
        formatted_tables.insert(0,formatted_table)

    return dict(zip(formatted_tables,tables))

def load_data_from_table(table_name):
    connection = pymysql.connect(**db_credentials, cursorclass=DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = f"SELECT * FROM {table_name}"
            cursor.execute(sql)
            data = cursor.fetchall()
    finally:
        connection.close()

    return pd.DataFrame(data)

def delete_table(table_name):
    connection = pymysql.connect(**db_credentials, cursorclass=DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = f"DROP TABLE {table_name}"
            cursor.execute(sql)
            connection.commit()
    finally:
        connection.close()

def create_dashboard(data):
    # Convert the timestamp to a pandas datetime object
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s').dt.strftime('%H:%M:%S.%f')

    # EAR time series plot
    fig_ear = px.line(data, x='timestamp', y='EAR', title='Eye Aspect Ratio (EAR) over Time')
    fig_ear.add_trace(go.Scatter(x=data['timestamp'], y=[thresholds["EAR_THRESH"]]*len(data), mode='lines', name='Threshold'))
    st.plotly_chart(fig_ear)
    # fig_ear= go.Figure()
    # fig_ear.add_scattergl(x=data["timestamp"],y=[thresholds["EAR_THRESH"] for i in range(len(data))], line={'color': 'white'})
    # fig_ear.add_scattergl(x=data["timestamp"],y=data["EAR"], line={'color': 'green'})
    # fig_ear.add_scattergl(x=data["timestamp"],y=data["EAR"].where(data["EAR"] <= thresholds["EAR_THRESH"]), line={'color':'red'})
    #st.plotly_chart(fig_ear)

    
    # MAR time series plot
    fig_mar = px.line(data, x='timestamp', y='MAR', title='Mouth Aspect Ratio (MAR) over Time')
    fig_mar.add_trace(go.Scatter(x=data['timestamp'], y=[thresholds["MAR_THRESH"]]*len(data), mode='lines', name='Threshold'))
    st.plotly_chart(fig_mar)
    # fig_mar= go.Figure()
    # fig_mar.add_scattergl(x=data["timestamp"],y=[thresholds["MAR_THRESH"] for i in range(len(data))], line={'color': 'white'})
    # fig_mar.add_scattergl(x=data["timestamp"],y=data["MAR"], line={'color': 'red'})
    # fig_mar.add_scattergl(x=data["timestamp"],y=data["MAR"].where(data["MAR"] <= thresholds["MAR_THRESH"]), line={'color':'green'})
    #st.plotly_chart(fig_mar)

    # Alarm_behaviour time series plot
    fig_alarm = px.line(data, x='timestamp', y='alarm_on', title='Alarm Behaviour over Time')
    st.plotly_chart(fig_alarm)

    # Eye shut counter and yawn counter
    st.subheader("Eye Shut & Yawn Counters")
    st.write(f"Eye Shut Counter: {data['eye_shut_counter'].max()}")
    st.write(f"Yawn Counter: {data['yawn_counter'].max()}")

    # Alarm count
    st.subheader("Alarm Count")
    st.write(f"Alarm triggered {data['alarm_counter'].max()} times during the trip")



def create_database(db_name):
    credentials= {"host": db_credentials["host"], "user": db_credentials["user"], "password": db_credentials["password"]}
    connection = pymysql.connect(**credentials, cursorclass=DictCursor)
    try:
        with connection.cursor() as cursor:
            sql= f"CREATE DATABASE IF NOT EXISTS {db_name}"
            cursor.execute(sql)
            connection.commit()
    finally:
        connection.close()

#def create_table_and_insert_data(df):
def create_table():
    connection = pymysql.connect(**db_credentials, cursorclass=DictCursor)
    try:
        with connection.cursor() as cursor:
            # Create a unique table name
            table_name = f"trip_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
            # Create the table
            sql_create = f"""
            CREATE TABLE {table_name} (
                timestamp DOUBLE,
                EAR DOUBLE,
                MAR DOUBLE,
                eye_shut_counter INT,
                yawn_counter INT,
                alarm_counter INT,
                alarm_on BOOLEAN
            )
            """
            cursor.execute(sql_create)
            connection.commit()

            # # Insert data from the DataFrame into the table
            # for _, row in df.iterrows():
                # sql_insert = f"""
                # INSERT INTO {table_name}
                # (timestamp, EAR, MAR, eye_shut_counter, yawn_counter, alarm_counter, alarm_on)
                # VALUES (%s, %s, %s, %s, %s, %s, %s)
                # """
            #     cursor.execute(sql_insert, row.to_list())
            #     connection.commit()
    finally:
        connection.close()
    
    st.session_state.curr_table_name = table_name


# Define the audio file to use.
path = os.path.dirname(__file__)
alarm_file_path = os.path.join(path,"audio", "wake_up.wav")

# Define pandas database that will be relayed to the backend MySQL database.
#drwsy_df=pd.DataFrame(columns=['timestamp', 'EAR', 'MAR', 'eye_shut_counter', 'yawn_counter', 'alarm_on'])
# if 'drwsy' not in st.session_state:
#         st.session_state['drwsy'] = pd.DataFrame(columns=['timestamp', 'EAR', 'MAR', 'eye_shut_counter', 'yawn_counter', 'alarm_on'])


# Streamlit Components
st.set_page_config(
    page_title="D3F",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Driver Drowsiness Detection and Feedback (D3F)",
    },
)

# if 'drwsy' not in st.session_state:
#         #st.session_state['drwsy'] = [pd.DataFrame(columns=['timestamp', 'EAR', 'MAR', 'eye_shut_counter', 'yawn_counter', 'alarm_counter', 'alarm_on'])]
#         st.session_state['drwsy'] = []

if "main_state" not in st.session_state:
    st.session_state.main_state = True

if "p2" not in st.session_state:
    st.session_state.p2 = False

if "p3" not in st.session_state:
    st.session_state.p3 = False

if "curr_table_name" not in st.session_state:
    st.session_state.curr_table_name = str()

if "selected" not in st.session_state:
    st.session_state.selected = str()

def main():
    st.title("D3F.io")
    st.subheader("Driver Drowsiness Detection and Feedback")

    prev_trip = st.button("View Previous Trips")
    start_trip = st.button("Start New Trip") 
    
    create_database(db_credentials["database"])

    if start_trip:
        create_table()
        st.session_state.p2 = True
        st.session_state.main_state = False
        st.session_state.p3 = False

    if prev_trip:
        st.session_state.p3 = True
        st.session_state.main_state = False
        st.session_state.p2 = False
        st.experimental_rerun()


def page2():

    st.title("Drowsiness Detection")
    
    
    # col1, col2 = st.columns(spec=[1, 1])
    
    # with col1:
    #     # Lowest valid value of Eye Aspect Ratio. Ideal values [0.15, 0.2].
    #     EAR_THRESH = st.slider("Eye Aspect Ratio threshold:", 0.0, 0.4, 0.18, 0.01)
    
    # with col2:
    #     # The amount of time (in seconds) to wait before sounding the alarm.
    #     WAIT_TIME = st.slider("Seconds to wait before sounding alarm:", 0.0, 5.0, 1.0, 0.25)
    
    
    # For streamlit-webrtc
    video_handler = VideoFrameHandler()
    audio_handler = AudioFrameHandler(sound_file_path=alarm_file_path)
    
    # For thread-safe access & to prevent race-condition.
    lock = threading.Lock()  
    
    #shared_state = {"play_alarm": False, "drwsy_df":pd.DataFrame(columns=['timestamp', 'EAR', 'MAR', 'eye_shut_counter', 'yawn_counter', 'alarm_on'])}
    
    #connection = pymysql.connect(**db_credentials, cursorclass=DictCursor)
    shared_state = {"play_alarm": False, "connection": pymysql.connect(**db_credentials, cursorclass=DictCursor), "table_name": st.session_state.curr_table_name}
    
    def video_frame_callback(frame: av.VideoFrame):
        frame = frame.to_ndarray(format="bgr24")  # Decode and convert frame to RGB
        #frame, play_alarm, row_dict = video_handler.process(frame, thresholds)  # Process frame
        frame, play_alarm = video_handler.process(frame, thresholds)  # Process frame

        with lock:
            shared_state["play_alarm"] = play_alarm  # Update shared state
            #shared_state['drwsy_df'] = pd.concat([shared_state['drwsy_df'], pd.DataFrame.from_records([row_dict])], ignore_index=True)
            #shared_state['drwsy_df'] = row_dict
            if video_handler.row_dict:
                sql_insert = f"""
                    INSERT INTO {shared_state["table_name"]}
                    (timestamp, EAR, MAR, eye_shut_counter, yawn_counter, alarm_counter, alarm_on)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                shared_state["connection"].cursor().execute(sql_insert, list(video_handler.row_dict.values()))
                shared_state["connection"].commit() 
        
        # Encode and return BGR frame
        return av.VideoFrame.from_ndarray(frame, format="bgr24")  
    
    def audio_frame_callback(frame: av.AudioFrame):
        with lock:  # access the current “play_alarm” state
            play_alarm = shared_state["play_alarm"]
    
        new_frame: av.AudioFrame = audio_handler.process(frame, play_sound=play_alarm)
        return new_frame

    # try:
    with shared_state["connection"].cursor():    
        ctx = webrtc_streamer(
            key="driver-drowsiness-detection",
            video_frame_callback=video_frame_callback,
            audio_frame_callback=audio_frame_callback,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            #media_stream_constraints={"video": {"width": True, "audio": True}},
            video_html_attrs=VideoHTMLAttributes(autoPlay=True, controls=False, muted=False)
        )
    # finally:
    #     connection.close()
    # try:
    #     while ctx.state.playing:
    #         with lock:
    #             row_dict = video_handler.row_dict
    #             row_dict_prev = video_handler.row_dict_prev
    #         if row_dict is None:
    #             continue
    #         elif row_dict:
    #             if row_dict != row_dict_prev:
    #                 #st.session_state['drwsy'] = pd.concat([st.session_state['drwsy'], pd.DataFrame.from_records([row_dict])], ignore_index=True)
    #                 #st.session_state['drwsy'].append(row_dict)
    #                 #print('bruh')
    #                 pass
    # except KeyError:
    #     pass

    if st.button("End Trip") or st.session_state.p3:
        shared_state["connection"].close()
        # Send the data in the dataframe df to the MySQL database
        # create_table_and_insert_data(shared_state['drwsy_df'])
        #create_table_and_insert_data(st.session_state['drwsy'])
        #create_table_and_insert_data(pd.DataFrame.from_records(st.session_state['drwsy']))
        # page3(video_handler.df)
        # page3(video_handler.getdf())
        st.session_state.p3 = True
        st.session_state.main_state = False
        st.session_state.p2 = False

    if st.button("Return Home", key="p2_to_main"):
        delete_table(st.session_state['curr_table_name'])
        st.session_state.p2 = False
        st.session_state.main_state = True
        st.session_state.p3 = False
        st.experimental_rerun()

def page3():
    st.title("Trip Information")
    
    # Fetch table names from the database
    names_dict = get_table_names()

    # Display the list of available tables
    selected_table = st.selectbox("Select a trip:", names_dict.keys())

    if selected_table:
        st.session_state["selected"]= names_dict[selected_table]
        st.session_state.p3 = True
        
        # Load data from the selected table
        trip_data = load_data_from_table(st.session_state["selected"])

        # Create the dashboard with the data
        if trip_data.empty == False:
            create_dashboard(trip_data)
        else:
            st.write("No Data In Table")
            
        if st.button("Delete Trip details"):
            delete_table(st.session_state["selected"])
            names_dict = get_table_names()
            st.session_state.p3=True
            st.session_state.main_state = False
            st.session_state.p2 = False
            st.experimental_rerun()


    if st.button("Return Home", key='p3_to_main'):
        st.session_state.p2 = False
        st.session_state.main_state = True
        st.session_state.p3 = False
        st.experimental_rerun()

    
if st.session_state.main_state:
    main()

if st.session_state.p2:
    page2()

if st.session_state.p3:
    page3()