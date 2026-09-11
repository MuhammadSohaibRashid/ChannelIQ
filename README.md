# ChannelIQ

> An AI-assisted video optimization and repurposing platform developed as a Final Year Project.

ChannelIQ helps creators transform long-form YouTube content into optimized, shareable media. It combines a React web interface with a Django REST backend and media-processing pipelines for transcription, captions, short-form clips, audio enhancement, video quality improvement, SEO support, and YouTube workflows.

## Why this project matters

The project demonstrates how a complete product can connect a modern frontend, an authenticated API, machine-learning services, media processing, cloud storage, and third-party platform integrations in one workflow.

## Core capabilities

- Fetch and process videos from YouTube URLs
- Generate captions and transcripts with Whisper-based speech recognition
- Create short-form clips with configurable duration and clip count
- Improve audio with noise reduction and loudness processing
- Enhance video quality with computer-vision and ONNX-based processing
- Generate SEO-oriented content for video publishing
- Compare original and optimized video output
- Store processed media through AWS S3 integration
- Authenticate users with Firebase and JWT-based application flows
- Connect to YouTube for authorized upload workflows
- Track processing tasks and generated media through the Django backend

## Technology stack

### Frontend

- React 18
- React Router
- Axios
- Firebase Authentication
- Font Awesome
- Responsive CSS components

### Backend

- Python 3
- Django 5
- Django REST Framework
- Simple JWT authentication
- CORS support
- SQLite for local development
- AWS S3 integration through Boto3

### AI and media processing

- OpenAI Whisper and faster-whisper for speech-to-text
- OpenCV and Ultralytics for computer vision
- ONNX Runtime for model inference
- MoviePy, FFmpeg, PyDub, Librosa, SoundFile, and SciPy for media processing
- YouTube Data API and yt-dlp for YouTube workflows
- OpenAI-powered and translation-related services where configured

## System architecture

```text
React frontend
    |
    | REST API / JWT
    v
Django + Django REST Framework
    |
    +-- Authentication and user workflows
    +-- Video and clip generation tasks
    +-- Caption and transcript services
    +-- SEO and optimization services
    +-- YouTube integration
    +-- AWS S3 media storage
    |
    +-- Whisper / OpenCV / ONNX / FFmpeg processing pipeline
```

## Typical workflow

1. A user signs in and submits a YouTube video URL.
2. The backend fetches the source metadata and media required for processing.
3. The user selects long-form optimization or short-form clip generation.
4. AI and media-processing services generate captions, clips, audio improvements, video enhancements, or SEO content.
5. Results are stored and made available through the dashboard and preview screens.
6. The user can compare outputs and use the YouTube upload workflow when configured.

## Repository structure

```text
.
├── README.md
├── .gitignore
└── test3-main/
    ├── backend/
    │   ├── manage.py
    │   ├── app/
    │   └── backend/
    ├── frontend/
    │   ├── package.json
    │   └── src/
    ├── requirements.txt
    └── Procfile
```

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/MuhammadSohaibRashid/channeliq.git
cd channeliq/test3-main
```

### 2. Configure backend environment variables

Create a local `.env` file for API keys and service configuration. Do not commit credentials. The Firebase service-account file and any OAuth client secrets must remain local and should be created from your own cloud project.

At minimum, review the backend settings and configure the services you plan to use:

- Django secret key and debug settings
- Firebase credentials
- AWS S3 credentials and bucket settings
- OpenAI or speech-processing credentials
- YouTube OAuth credentials
- Frontend and backend allowed origins

### 3. Install backend dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirement.txt
python manage.py migrate
python manage.py runserver
```

### 4. Install and run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm start
```

The frontend runs on `http://localhost:3000` and the Django API runs on `http://localhost:8000` by default.

## Security and repository hygiene

This project uses external services and local development credentials. Never commit Firebase service-account files, OAuth client secrets, `.env` files, local databases, generated media, model weights, or dependency folders. Use environment variables and documented setup steps for deployment.

## Project status

This repository contains the Final Year Project implementation and is being prepared as a portfolio-ready software project. Some AI and cloud workflows require valid service credentials and locally installed media-processing dependencies.

## Skills demonstrated

- Full-stack application development
- REST API design and frontend integration
- Authentication and authorization
- AI-assisted speech and video processing
- Computer vision and model inference
- Audio engineering and media pipelines
- Cloud storage and third-party API integration
- Asynchronous task and job-status handling
- Database-backed application development
- Responsive product interface design
- Git and GitHub project organization

## Author

**Muhammad Sohaib Rashid**

Final Year Project: ChannelIQ, an AI-assisted video optimization and repurposing platform.
