Driver Drowsiness Detection and Feedback (D3F)

This app analyses facial landmarks to detect if the driver of the vehicle is drowsy/distracted and promptly alerts them. It uses Google's MediaPipe library to capture facial features, which are then processed to detect if the driver's eyes are distracted or drowsy, and also if the driver is yawning excessively. Based on these metrics, the app sounds an alarm to alert the driver. The app metrics are also preserved in a MySQL database and are utilized by a Ride summary dashboard shown to the driver at the end of the trip. The frontend is made using Streamlit, and the backend is housed in a MySQL database. 

The final iteration of the project is contained in the D3F_Final directory

The following screenshots show what the app's UI looks like:

Main page:

![alt text](https://github.com/sreeman-reddy/D3F/blob/main/example1.jpg "main screen")

Previous Trips page:

![alt text](https://github.com/sreeman-reddy/D3F/blob/main/example2.jpg "trip info")

Trip UI (Facial tracking):

![alt text](https://github.com/sreeman-reddy/D3F/blob/main/example3.jpg "tripUI")

Trip UI (drowsiness detected):

![alt text](https://github.com/sreeman-reddy/D3F/blob/main/example4.jpg "tripUI drowsy")

Post Trip analysis:

![alt text](https://github.com/sreeman-reddy/D3F/blob/main/example5.jpg "post trip 1")

![alt text](https://github.com/sreeman-reddy/D3F/blob/main/example6.jpg "post trip 2")


