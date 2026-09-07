## Pothole Detection and Traffic Analysis

An AI-based web application that detects potholes in real time and analyzes traffic conditions using live traffic, weather, and route information.

### Project Overview

This project combines YOLOv8-based pothole detection with traffic analysis to support road safety and route decision-making.

The pothole detection module uses a camera to detect and count potholes in real time. Based on the number of detected potholes, the system classifies the road condition and traffic risk.

The traffic analysis module takes a source and destination, retrieves location, weather, and real-time traffic information, and provides an alternative route when traffic conditions require it.

### Technologies Used

- Python
- Flask
- YOLOv8
- OpenCV
- MySQL
- HTML
- CSS
- REST APIs

### APIs Used

- OpenStreetMap Nominatim - Location geocoding
- TomTom Routing API - Real-time traffic and route information
- OpenWeather API - Weather information

### Features

### Pothole Detection

- Real-time camera-based pothole detection
- YOLOv8 object detection
- Pothole counting
- Road risk classification
- Road condition identification

### Traffic Analysis

- Source and destination selection
- Location geocoding
- Real-time traffic analysis
- Current weather information
- Traffic status classification
- Alternative route suggestion

### Risk Classification

The pothole detection module classifies road conditions based on the number of detected potholes:

| Potholes Detected | Risk Level | Road Condition |
|---|---|---|
| 0 | Low | Safe |
| 1–3 | Medium | Caution |
| More than 3 | High | High Risk |

### Traffic Classification

Traffic conditions are classified using:

- Real-time traffic delay
- Weather conditions
- Peak-hour conditions

The final traffic status is classified as:

- Low
- Moderate
- High

### Machine Learning Model

The pothole detection system uses a trained YOLOv8 model for real-time object detection.

The model detects potholes from camera frames and draws bounding boxes around detected objects.

### Web Application

The application is developed using Flask and provides pages for:

- Home
- About
- Methodology
- User Registration
- User Login
- Pothole Prediction
- Traffic Analysis

### Database

MySQL is used for storing user registration and login information.

### Project Structure

```text
Pothole-Detection-and-Traffic-Analysis/
│
├── static/
│   ├── uploads/
│   └── results/
│
├── templates/
│
├── app.py
├── best (4).pt
└── README.md
