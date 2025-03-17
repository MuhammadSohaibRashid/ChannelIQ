import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urllib.parse import urlparse, parse_qs
import boto3
import yt_dlp
import logging
from rest_framework import status
from rest_framework.permissions import AllowAny
from google.auth.transport import requests
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from google.oauth2 import id_token
from django.shortcuts import redirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import subprocess
from moviepy.editor import VideoFileClip
logger = logging.getLogger(__name__)
import json
import re
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from .utils.SEO import EnhancedYouTubeSEOGenerator
from .utils.Audio.audio import AudioEnhancer
from .utils.clips.clips2.main import process_video
from .utils.fetchData import fetch_video_metadata
from .utils.video.anas import process_media
from .utils.video.anas import process_media_shortform
from .utils.Captions import DjangoVideoTranscriber
from .utils.s3uploader import S3Uploader
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Ensure the YouTube API key is set in environment variables
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise ValueError("YouTube API Key not set. Please configure it in environment variables.")
MEDIA_ROOT = os.path.join(os.getcwd(), 'media')

@csrf_exempt
def process_short_form_video(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            video_url = data.get("videoURL")
            clip_length = data.get("clipLength")  # Extract clipLength
            clip_count = data.get("clipCount")   # Extract clipCount
            clip_length=int(clip_length)
            # Debugging log
            logger.info(f"Received video URL: {video_url}, Clip Length: {clip_length}, Clip Count: {clip_count}")

            # Validate input
            if not video_url or not clip_length or not clip_count:
                return JsonResponse({"error": "Missing required parameters: videoURL, clipLength, or clipCount"}, status=400)

            # Call the process_video function directly
            clips = process_video(video_url, clip_length, clip_count,MEDIA_ROOT)

            if clips:
                # Extract clip paths
                clip_paths = [clip["clip_path"] for clip in clips]

                # Debugging log
                logger.info(f"Generated clip paths: {clip_paths}")

                # Return a successful response with the clip paths
                return JsonResponse({
                    "message": "Video processed successfully",
                    "clips": clip_paths
                }, status=200)
            else:
                # Handle case where no clips were generated
                return JsonResponse({"error": "Failed to generate clips from the video"}, status=500)

        except json.JSONDecodeError:
            logger.error("Invalid JSON data in request body")
            return JsonResponse({"error": "Invalid JSON data in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error in process_short_form_video: {e}")
            return JsonResponse({"error": "Internal Server Error"}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

def get_video_resolution(video_path):
    """Gets the resolution (width x height) of the video."""
    with VideoFileClip(video_path) as video:
        width, height = video.size  # (width, height)
    return width, height

@csrf_exempt
def check_resolution(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            video_path = data.get("video_path")



            # Normalize and verify the path
            video_path = os.path.normpath(video_path)


            try:
                # Use ffprobe to extract video dimensions
                cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "json", video_path
                ]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if result.returncode != 0:
                    return JsonResponse({
                        "resolution": None,
                        "error": "Failed to retrieve video resolution",
                        "details": result.stderr
                    }, status=500)

                metadata = json.loads(result.stdout)
                width = metadata['streams'][0]['width']
                height = metadata['streams'][0]['height']

                return JsonResponse({
                    "resolution": {
                        "width": width,
                        "height": height
                    },
                    "error": None
                })

            except Exception as e:
                return JsonResponse({
                    "resolution": None,
                    "error": f"Error reading video file: {str(e)}"
                }, status=500)

        except json.JSONDecodeError as e:
            return JsonResponse({
                "resolution": None,
                "error": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "resolution": None,
                "error": f"Server error: {str(e)}"
            }, status=500)

    return JsonResponse({
        "resolution": None,
        "error": "Only POST method is allowed"
    }, status=405)
@csrf_exempt
def seo(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            video_url = data.get("videoURL")
            localpath = data.get("localVideoPath")
            selected_features = data.get("selectedFeatures", [])  # Extract selected features

            # Debugging log
            logger.info(f"Received video URL for SEO: {video_url}, Selected Features: {selected_features}, LocalPath: {localpath}")

            if not video_url and not localpath:
                return JsonResponse({"error": "No URL or local path provided"}, status=400)

            # Define the order of feature processing
            feature_order = ["SEO", "Video Quality", "Noise Reduction"]
            selected_features = sorted(
                selected_features,
                key=lambda feature: feature_order.index(feature) if feature in feature_order else len(feature_order)
            )
            logger.info(f"Selected features after sort: {selected_features}")

            # Initialize a dictionary to store the results for all selected features
            results = {}

            # Check video resolution before processing
            video_resolution = None
            if localpath:
                try:
                    width, height = get_video_resolution(localpath)
                    logger.info(f"Video Resolution: {width}x{height}")
                    video_resolution = (width, height)
                except Exception as e:
                    logger.error(f"Error getting video resolution: {e}")
                    results["video_upscaling"] = {"error": "Failed to get video resolution"}

            # Handle SEO feature
            if "SEO" in selected_features:
                try:
                    if video_url:
                        seo_generator = EnhancedYouTubeSEOGenerator()
                        seo_data = seo_generator.process_video(video_url)
                        results["seo"] = seo_data
                except Exception as e:
                    logger.error(f"Error in SEO processing: {e}")
                    results["seo"] = {"error": str(e)}

            # Handle Video Quality feature
            upscaled_video_path = None
            if "Video Quality" in selected_features and localpath:
                try:
                    # Only proceed with upscaling if the resolution is less than or equal to 480p (height <= 480)
                    if video_resolution and video_resolution[1] <= 480:
                        upscaled_video_path = process_media(
                            file_path=localpath,
                            ai_model="RealESR_Gx4",
                            resize_factor=100,  # Example value, adjust as needed
                            output_path=None,  # Use default output path
                            cpu_number=4,
                            keep_frames=False,
                        )
                        results["video_upscaling"] = {"processed_file_path": upscaled_video_path}
                    else:
                        results["video_upscaling"] = {"message": "Resolution is greater than 480p, skipping upscaling."}
                except Exception as e:
                    logger.error(f"Error in video upscaling: {e}")
                    results["video_upscaling"] = {"error": str(e)}

            # Handle Noise Reduction feature
            if "Noise Reduction" in selected_features:
                try:
                    clip_path = upscaled_video_path or localpath
                    if clip_path:
                        # Create output directory if it doesn't exist
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Initialize AudioEnhancer (without path parameter - it's not needed in constructor)
                        audio_enhancer = AudioEnhancer()
                        
                        # Process the video
                        process_result = audio_enhancer.process_video(
                            video_path=str(clip_path),
                            output_dir=str(output_dir)
                        )
                        
                        # Get the enhanced video path from the result
                        enhanced_video_path = process_result.get('enhanced_video_path')
                        
                        if enhanced_video_path and os.path.exists(enhanced_video_path):
                            results["audio_processing"] = {
                                "processed_file_path": enhanced_video_path,
                                "status": "success"
                            }
                        else:
                            results["audio_processing"] = {
                                "error": "Enhanced video file not found",
                                "status": "error"
                            }
                    else:
                        results["audio_processing"] = {
                            "error": "Clip path not provided",
                            "status": "error"
                        }
                except Exception as e:
                    logger.error(f"Error in audio processing: {str(e)}")
                    results["audio_processing"] = {
                        "error": str(e),
                        "status": "error"
                    }

            # Return results after processing all selected features
            return JsonResponse({
                "message": "Processing completed successfully",
                "results": results
            }, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON data in request body")
            return JsonResponse({"error": "Invalid JSON data in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error in SEO function: {e}")
            return JsonResponse({"error": "Internal Server Error"}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

@csrf_exempt
def optimize_shortform(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            clip_paths = data.get("clipPaths", [])
            selected_features = data.get("selectedFeatures", [])

            # Debugging log
            logger.info(f"Received clip paths for optimization: {clip_paths}, Selected Features: {selected_features}")

            if not clip_paths:
                return JsonResponse({"error": "No clip paths provided"}, status=400)

            # Sort features to ensure Video Quality comes before Noise Reduction
            feature_order = ["SEO", "Video Quality", "Noise Reduction", "Captions"]
            selected_features = sorted(
                selected_features,
                key=lambda feature: feature_order.index(feature) if feature in feature_order else len(feature_order)
            )
            logger.info(f"Selected features after sort: {selected_features}")

            results = {}

            for clip_path in clip_paths:
                clip_results = {}
                current_clip_path = clip_path
                print(current_clip_path)  

                # Clean up the path (remove the media URL prefix if present)
                if clip_path.startswith("http://127.0.0.1:8000/media/"):
                    clip_path = clip_path.replace("http://127.0.0.1:8000/media/", "")

                local_clip_path = os.path.join("media", clip_path)  # Use relative path
                current_clip_path = local_clip_path  # Update working path
                logger.info(f"Initial local clip path: {local_clip_path}")

                if not os.path.exists(local_clip_path):
                    clip_results["error"] = f"Clip path {clip_path} does not exist on the server."
                    results[clip_path] = clip_results
                    continue

                # Handle SEO feature
                if "SEO" in selected_features:
                    try:
                        seo_generator = EnhancedYouTubeSEOGenerator(current_clip_path)
                        seo_data = seo_generator.process_video_shortform(current_clip_path)
                        clip_results["seo"] = seo_data
                    except Exception as e:
                        logger.error(f"Error in SEO processing for {clip_path}: {e}")
                        clip_results["seo"] = {"error": str(e)}

                upscaled_video_path = None
                # Handle Video Quality feature
                if "Video Quality" in selected_features:
                    try:
                        upscaled_video_path = process_media_shortform(
                            file_path=current_clip_path,
                            ai_model="IRCNN_Lx1",  # Example model, adjust as needed
                            resize_factor=100,  # Example value, adjust as needed
                            output_path=None,  # Use default output path
                            cpu_number=4,  # Example value, adjust as needed
                            keep_frames=False,  # Example value, adjust as needed
                        )
                        clip_results["video_upscaling"] = {"processed_file_path": upscaled_video_path}

                        # Update the current working path to the upscaled video
                        current_clip_path = upscaled_video_path
                        logger.info(f"Updated path after video processing: {current_clip_path}")
                    except Exception as e:
                        logger.error(f"Error in video upscaling for {clip_path}: {e}")
                        clip_results["video_upscaling"] = {"error": str(e)}
                enhanced_video_path=None
                # Handle Noise Reduction feature
                if "Noise Reduction" in selected_features:
                    try:
                        clip_path = upscaled_video_path or current_clip_path
                        if clip_path:
                            # Create output directory if it doesn't exist
                            output_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
                            os.makedirs(output_dir, exist_ok=True)
                            
                            # Initialize AudioEnhancer (without path parameter - it's not needed in constructor)
                            audio_enhancer = AudioEnhancer()
                            
                            # Process the video
                            process_result = audio_enhancer.process_video(
                                video_path=str(clip_path),
                                output_dir=str(output_dir)
                            )
                            
                            # Get the enhanced video path from the result
                            enhanced_video_path = process_result.get('enhanced_video_path')
                            
                            if enhanced_video_path and os.path.exists(enhanced_video_path):
                                clip_results["audio_processing"] = {
                                    "processed_file_path": enhanced_video_path,
                                    "status": "success"
                                }
                            else:
                                clip_results["audio_processing"] = {
                                    "error": "Enhanced video file not found",
                                    "status": "error"
                                }
                        else:
                            clip_results["audio_processing"] = {
                                "error": "Clip path not provided",
                                "status": "error"
                            }
                    except Exception as e:
                        logger.error(f"Error in audio processing: {str(e)}")
                        clip_results["audio_processing"] = {
                            "error": str(e),
                            "status": "error"
                        }

                # Handle Captions feature (last step)
                if "Captions" in selected_features:
                    try:
                        # Use the final processed video path (upscaled or noise-reduced)
                        final_video_path = enhanced_video_path or upscaled_video_path or current_clip_path

                        # Initialize the DjangoVideoTranscriber
                        transcriber = DjangoVideoTranscriber(
                            model_path="turbo",  # Replace with actual model path
                            video_path=final_video_path
                        )

                        # Process the video to add captions
                        captioned_video_path = transcriber.process_video()

                        # Update the results with the captioned video path
                        clip_results["captions"] = {
                            "processed_file_path": captioned_video_path,
                            "status": "success"
                        }

                        # Update the current working path to the captioned video
                        current_clip_path = captioned_video_path
                        logger.info(f"Updated path after captioning: {current_clip_path}")

                    except Exception as e:
                        logger.error(f"Error in captioning for {clip_path}: {e}")
                        clip_results["captions"] = {"error": str(e)}


            return JsonResponse({
                "message": "Processing completed successfully",
                "results": clip_results
            }, status=200)

        except json.JSONDecodeError:
            logger.error("Invalid JSON data in request body")
            return JsonResponse({"error": "Invalid JSON data in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error in optimize_shortform function: {e}")
            return JsonResponse({"error": f"Internal Server Error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
@csrf_exempt
def fetch_data(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            video_url = data.get("videoURL")

            # Validate the video URL
            if not video_url:
                return JsonResponse({"error": "No video URL provided"}, status=400)

            try:
                # Call the fetch_video_metadata function directly
                video_metadata = fetch_video_metadata(video_url)

                if video_metadata:
                    return JsonResponse({
                        "message": "Video metadata fetched successfully",
                        "data": video_metadata
                    })
                else:
                    return JsonResponse({"error": "Failed to fetch video metadata"}, status=500)

            except Exception as e:
                logger.error(f"Error in fetch_video_metadata: {str(e)}")
                return JsonResponse({"error": "Error fetching video metadata", "details": str(e)}, status=500)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {str(e)}")
            return JsonResponse({
                "error": "Invalid JSON in request body",
                "details": str(e)
            }, status=400)

        except Exception as e:
            logger.error(f"Unexpected error in fetch_data: {str(e)}")
            return JsonResponse({
                "error": "Internal server error",
                "details": str(e)
            }, status=500)

    return JsonResponse({
        "error": "Only POST method is allowed"
    }, status=405)

def extract_video_id(video_url):
    try:
        parsed_url = urlparse(video_url)
        if parsed_url.netloc in ["www.youtube.com", "youtube.com"]:
            query_params = parse_qs(parsed_url.query)
            return query_params.get("v", [None])[0]
        elif parsed_url.netloc == "youtu.be":
            return parsed_url.path.strip("/")
        return None
    except Exception as e:
        logger.error(f"Error extracting video ID: {e}")
        return None
def upload_video(request):
    if request.method == 'POST' and request.FILES['video']:
        video = request.FILES['video']
        fs = FileSystemStorage(location=settings.MEDIA_ROOT)
        filename = fs.save(video.name, video)
        file_url = fs.url(filename)
        return JsonResponse({'file_url': file_url})
# Fetch Video Metadata
@csrf_exempt
def fetch_video_data(request):
    video_url = request.GET.get("url")
    if not video_url:
        return JsonResponse({"error": "No URL provided"}, status=400)

    video_id = extract_video_id(video_url)
    if not video_id:
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        response = youtube.videos().list(part="snippet", id=video_id).execute()

        if "items" not in response or not response["items"]:
            return JsonResponse({"error": "Video not found"}, status=404)

        video_data = response["items"][0]["snippet"]
        return JsonResponse({
            "title": video_data["title"],
            "thumbnail": video_data["thumbnails"]["high"]["url"],
        })

    except HttpError as e:
        logger.error(f"Error fetching video metadata: {e}")
        return JsonResponse({"error": f"Error fetching video metadata: {e}"}, status=500)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return JsonResponse({"error": f"An unexpected error occurred: {e}"}, status=500)
def sanitize_filename(filename):
    # Remove any characters that are not allowed in filenames
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # Remove invalid characters
    return filename
# Download Video and Upload to S3
@csrf_exempt
def download_video(request):
    # Extract video URL from the request
    if request.method == "POST":
        video_url = request.POST.get("url")
    else:
        video_url = request.GET.get("url")

    # Validate the video URL
    if not video_url:
        return JsonResponse({"error": "No URL provided"}, status=400)

    # Extract video ID from the URL
    video_id = extract_video_id(video_url)
    if not video_id:
        return JsonResponse({"error": "Invalid YouTube URL"}, status=400)

    # Define the local save path using MEDIA_ROOT
    sanitized_filename = sanitize_filename(f"{video_id}.mp4")
    local_file_path = os.path.join(settings.MEDIA_ROOT, "videos", sanitized_filename)

    # Ensure the videos directory exists
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

    # Check if the file already exists locally
    if os.path.exists(local_file_path):
        logger.debug(f"Video already exists locally: {local_file_path}")

        # Check if it also exists in S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        s3_key = f"videos/{video_id}.mp4"

        try:
            # Check if file exists in S3 bucket
            s3_client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
            video_url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            return JsonResponse({
                "message": "Video already exists.",
                "url": video_url_s3,
                "local_path": local_file_path
            })
        except s3_client.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                # File exists locally but not in S3, upload it
                try:
                    logger.debug(f"Uploading existing local file to S3")
                    s3_client.upload_file(local_file_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
                    video_url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                    return JsonResponse({
                        "message": "Existing video uploaded to S3.",
                        "url": video_url_s3,
                        "local_path": local_file_path
                    })
                except Exception as upload_error:
                    logger.error(f"Failed to upload existing file to S3: {str(upload_error)}")
                    return JsonResponse({
                        "message": "File exists locally but S3 upload failed.",
                        "local_path": local_file_path
                    })

    # If file doesn't exist locally, proceed with download
    try:
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]',
            'outtmpl': local_file_path,
            'quiet': False,
            'logger': logger,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug(f"Downloading video: {video_url}")
            ydl.download([video_url])

        if not os.path.exists(local_file_path):
            return JsonResponse({"error": "Downloaded file not found."}, status=500)

        # Upload to S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        s3_key = f"videos/{video_id}.mp4"
        logger.debug(f"Uploading to S3 bucket: {settings.AWS_STORAGE_BUCKET_NAME}, key: {s3_key}")
        s3_client.upload_file(local_file_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        video_url_s3 = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        return JsonResponse({
            "message": "Video uploaded successfully.",
            "url": video_url_s3,
            "local_path": local_file_path
        })

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"Download failed: {str(e)}")
        return JsonResponse({"error": f"Download error: {str(e)}"}, status=500)
    except boto3.exceptions.S3UploadFailedError as e:
        logger.error(f"S3 upload failed: {str(e)}")
        return JsonResponse({"error": f"S3 upload failed: {str(e)}"}, status=500)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)
def get_video(request, video_id):
    """Get video URL by video ID"""
    # Initialize S3 uploader
    s3_uploader = S3Uploader(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
        region=getattr(settings, 'AWS_S3_REGION_NAME', None)
    )

    s3_key = f"videos/{video_id}.mp4"

    # Check if the file exists in S3
    if s3_uploader.file_exists_in_s3(s3_key):
        video_url = s3_uploader.get_s3_url(s3_key)
        return JsonResponse({
            "video_id": video_id,
            "url": video_url
        })
    else:
        return JsonResponse({
            "error": "Video not found"
        }, status=404)
# YouTube API scopes needed for video upload
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_auth(request):
    auth_header = request.headers.get('Authorization', 'No Token Provided')
    print(f"🔍 Received Authorization Header: {auth_header}")
    print(f"👤 Authenticated User: {request.user if request.user.is_authenticated else 'Not Authenticated'}")

    if not request.user.is_authenticated:
        return Response({'error': 'User not authenticated'}, status=401)

    return Response({'is_authorized': True})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def authorize_youtube(request):
    """Initiate YouTube authorization flow"""
    # Create OAuth 2.0 flow instance
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'client_secret.json'),
        scopes=SCOPES
    )
    
    # Set redirect URI
    flow.redirect_uri = request.build_absolute_uri('/api/youtube/callback/')
    
    # Generate authorization URL and state
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force to always prompt for consent to get refresh token
    )
    
    # Store state in session
    request.session['youtube_auth_state'] = state
    request.session['user_id'] = request.user.id
    
    # Redirect to authorization URL
    return redirect(authorization_url)

@api_view(['GET', 'POST'])
@csrf_exempt
def youtube_callback(request):
    """Handle callback from YouTube authorization"""
    # Get state from session
    state = request.session.get('youtube_auth_state')
    user_id = request.session.get('user_id')
    
    if not state or not user_id:
        return JsonResponse({'error': 'Invalid state'}, status=400)
    
    # Get authorization code from request
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'No authorization code'}, status=400)
    
    # Create flow instance
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'client_secret.json'),
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = request.build_absolute_uri('/api/youtube/callback/')
    
    # Exchange authorization code for access token
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # Save credentials to database
    from .models import YouTubeAuth
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.get(id=user_id)
    
    youtube_auth, created = YouTubeAuth.objects.get_or_create(user=user)
    youtube_auth.credentials = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    youtube_auth.save()
    
    # Redirect to frontend callback page
    frontend_callback_url = settings.FRONTEND_URL + '/youtube-auth-callback'
    return redirect(frontend_callback_url + '?code=' + code)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_video(request):
    """Upload video to YouTube"""
    user = request.user
    
    # Check if user has valid YouTube credentials
    try:
        youtube_auth = user.youtubeauth
        if not youtube_auth.is_valid():
            return Response({'error': 'YouTube authorization has expired'}, status=401)
    except:
        return Response({'error': 'YouTube authorization required'}, status=401)
    
    # Get video file and metadata
    video_file = request.FILES.get('video')
    title = request.POST.get('title')
    description = request.POST.get('description')
    tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []
    
    if not video_file:
        return Response({'error': 'No video file provided'}, status=400)
    
    if not title:
        return Response({'error': 'Title is required'}, status=400)
    
    # Save video file temporarily
    import tempfile
    import os
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    for chunk in video_file.chunks():
        temp_file.write(chunk)
    temp_file.close()
    
    try:
        # Get credentials from database
        creds_data = youtube_auth.credentials
        credentials = google.oauth2.credentials.Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )
        
        # Create YouTube service
        youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
        
        # Create video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22'  # People & Blogs category
            },
            'status': {
                'privacyStatus': 'private',  # Start as private, can be changed later
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Upload video file
        media = MediaFileUpload(
            temp_file.name,
            mimetype='video/mp4',
            resumable=True
        )
        
        # Execute upload request
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        response = request.execute()
        
        # Update credentials if they were refreshed
        if credentials.token != creds_data.get('token'):
            youtube_auth.credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            youtube_auth.save()
        
        # Return video ID
        return Response({'success': True, 'video_id': response['id']})
        
    except Exception as e:
        print(f"YouTube upload error: {str(e)}")
        return Response({'error': str(e)}, status=500)
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    """Verify Google token and create/login user"""
    token = request.data.get('token')
    
    if not token:
        return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_OAUTH_CLIENT_ID
        )
        
        if 'email' not in idinfo:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

        # Extract user details
        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')

        # Find or create the user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,  
                'first_name': name.split(' ')[0] if ' ' in name else name,
                'last_name': name.split(' ')[1] if ' ' in name else '',
                'is_active': True,
            }
        )

        # Generate authentication token
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': name,
                'picture': picture,
                'is_new': created
            }
        })
        
    except ValueError:
        return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        print(f"Google Auth Error: {str(e)}") 
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)