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
import time
User = get_user_model()
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
            clip_length = data.get("clipLength")
            clip_count = data.get("clipCount")
            
            # Debugging log
            logger.info(f"Received video URL: {video_url}, Clip Length: {clip_length}, Clip Count: {clip_count}")

            # Validate input
            if not video_url:
                return JsonResponse({"error": "Missing required parameter: videoURL"}, status=400)
            
            # Convert clip_count to int if it exists, otherwise use default
            try:
                clip_count = int(clip_count) if clip_count else 3  # Default to 3 clips
            except (ValueError, TypeError):
                logger.warning(f"Invalid clipCount: {clip_count}, using default of 3")
                clip_count = 3
            
            # Handle clip_length
            if not clip_length:
                clip_length = "auto"  # Default to auto if not provided
            
            # Call the process_video function directly
            clips = process_video(video_url, clip_length, clip_count, MEDIA_ROOT)

            if clips:
                # Initialize S3Uploader
                s3_uploader = S3Uploader(
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                    region=settings.AWS_S3_REGION_NAME
                )

                # Get user ID from the request
                user_id = request.user.sub if request.user.is_authenticated else "anonymous"
                
                # Upload each clip to S3 and get S3 URLs
                s3_clip_urls = []
                for idx, clip in enumerate(clips):
                    local_file_path = os.path.join(MEDIA_ROOT, clip["clip_path"])
                    video_id = f"clip_{idx}_{int(time.time())}"
                    s3_key = s3_uploader.get_user_video_key(user_id, video_id)
                    
                    # Upload to S3
                    upload_result = s3_uploader.upload_file(local_file_path, s3_key)
                    
                    if upload_result["success"]:
                        s3_clip_urls.append({
                            "url": upload_result["url"],
                            "key": upload_result["key"]
                        })
                    else:
                        logger.error(f"Failed to upload clip to S3: {upload_result['error']}")
                
                # Debugging log
                logger.info(f"Generated S3 clip URLs: {s3_clip_urls}")

                # Return a successful response with the S3 clip URLs
                return JsonResponse({
                    "message": "Video processed successfully",
                    "clips": s3_clip_urls
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
            user_id = data.get("userId")
            print("User ID=",user_id)  # Get user ID from the request

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

            # Handle Video Quality feature - LOCAL processing
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
                        results["video_upscaling"] = {
                            "processed_file_path": upscaled_video_path,
                            "status": "success"
                        }
                    else:
                        results["video_upscaling"] = {"message": "Resolution is greater than 480p, skipping upscaling."}
                except Exception as e:
                    logger.error(f"Error in video upscaling: {e}")
                    results["video_upscaling"] = {"error": str(e)}

            # Handle Noise Reduction feature - LOCAL processing
            enhanced_audio_path = None
            if "Noise Reduction" in selected_features:
                try:
                    clip_path = upscaled_video_path or localpath
                    if clip_path:
                        # Create output directory if it doesn't exist
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Initialize AudioEnhancer
                        audio_enhancer = AudioEnhancer()
                        
                        # Process the video
                        process_result = audio_enhancer.process_video(
                            video_path=str(clip_path),
                            output_dir=str(output_dir)
                        )
                        
                        # Get the enhanced video path from the result
                        enhanced_audio_path = process_result.get('enhanced_video_path')
                        
                        if enhanced_audio_path and os.path.exists(enhanced_audio_path):
                            results["audio_processing"] = {
                                "processed_file_path": enhanced_audio_path,
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
            
            # FINAL S3 UPLOAD - Upload the final processed video to S3
            final_video_path = enhanced_audio_path or upscaled_video_path or localpath
            
            # Only upload if we have a user ID and a processed video
            if user_id and final_video_path and os.path.exists(final_video_path):
                try:
                    # Initialize S3 uploader
                    s3_uploader = S3Uploader(
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                        region=settings.AWS_S3_REGION_NAME
                    )
                    
                    # Generate a unique video ID based on processing features
                    feature_string = "-".join(selected_features).lower().replace(" ", "-")
                    video_id = f"{feature_string}_{os.path.basename(final_video_path).split('.')[0]}"
                    
                    # Upload to S3
                    s3_key = s3_uploader.get_user_video_key(user_id, video_id)
                    upload_result = s3_uploader.upload_file(final_video_path, s3_key)
                    
                    if upload_result["success"]:
                        # Add S3 information to results
                        results["s3_upload"] = {
                            "url": upload_result["url"],
                            "key": upload_result["key"],
                            "status": "success"
                        }
                        
                        # Update the processed file path in the final results to use the S3 URL
                        if enhanced_audio_path:
                            results["audio_processing"]["s3_processed_file_path"] = upload_result["url"]
                        elif upscaled_video_path:
                            results["video_upscaling"]["s3_processed_file_path"] = upload_result["url"]
                    else:
                        results["s3_upload"] = {
                            "error": f"Failed to upload to S3: {upload_result.get('error')}",
                            "status": "error"
                        }
                except Exception as e:
                    logger.error(f"Error uploading to S3: {str(e)}")
                    results["s3_upload"] = {
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
            clip_path = data.get("clipPath")
            clip_key = data.get("clipKey")
            selected_features = data.get("selectedFeatures", [])

            # Debugging log
            logger.info(f"Received clip for optimization: {clip_path}, Key: {clip_key}, Selected Features: {selected_features}")

            if not clip_path or not clip_key:
                return JsonResponse({"error": "No clip path or key provided"}, status=400)

            # Sort features to ensure Video Quality comes before Noise Reduction
            feature_order = ["SEO", "Video Quality", "Noise Reduction", "Captions"]
            selected_features = sorted(
                selected_features,
                key=lambda feature: feature_order.index(feature) if feature in feature_order else len(feature_order)
            )
            logger.info(f"Selected features after sort: {selected_features}")

            # Initialize S3 uploader with credentials from settings
            s3_uploader = S3Uploader(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                region=settings.AWS_S3_REGION_NAME
            )
            
            # Download the clip from S3 to local media folder
            local_dir = os.path.join(settings.MEDIA_ROOT, 'temp_downloads')
            os.makedirs(local_dir, exist_ok=True)
            
            filename = os.path.basename(clip_key)
            local_clip_path = os.path.join(local_dir, filename)
            
            # Download file from S3
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                s3_client.download_file(settings.AWS_STORAGE_BUCKET_NAME, clip_key, local_clip_path)
                logger.info(f"Successfully downloaded clip from S3 to {local_clip_path}")
            except Exception as e:
                logger.error(f"Error downloading clip from S3: {e}")
                return JsonResponse({"error": f"Failed to download clip from S3: {str(e)}"}, status=500)
            
            # Initialize results dictionary
            results = {}
            current_clip_path = local_clip_path  # Start with downloaded file
            
            # Process SEO if selected
            if "SEO" in selected_features:
                try:
                    seo_generator = EnhancedYouTubeSEOGenerator(current_clip_path)
                    seo_data = seo_generator.process_video_shortform(current_clip_path)
                    results["seo"] = seo_data
                except Exception as e:
                    logger.error(f"Error in SEO processing: {e}")
                    results["seo"] = {"error": str(e)}
            
            # Process Video Quality if selected
            upscaled_video_path = None
            if "Video Quality" in selected_features:
                try:
                    upscaled_video_path = process_media_shortform(
                        file_path=current_clip_path,
                        ai_model="IRCNN_Lx1",
                        resize_factor=100,
                        output_path=None,
                        cpu_number=4,
                        keep_frames=False,
                    )
                    results["video_upscaling"] = {"processed_file_path": upscaled_video_path}
                    
                    # Update current working path
                    current_clip_path = upscaled_video_path
                    logger.info(f"Updated path after video processing: {current_clip_path}")
                except Exception as e:
                    logger.error(f"Error in video upscaling: {e}")
                    results["video_upscaling"] = {"error": str(e)}
            
            # Process Noise Reduction if selected
            enhanced_video_path = None
            if "Noise Reduction" in selected_features:
                try:
                    if current_clip_path:
                        # Create output directory if it doesn't exist
                        output_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Process audio
                        audio_enhancer = AudioEnhancer()
                        process_result = audio_enhancer.process_video(
                            video_path=str(current_clip_path),
                            output_dir=str(output_dir)
                        )
                        
                        enhanced_video_path = process_result.get('enhanced_video_path')
                        
                        if enhanced_video_path and os.path.exists(enhanced_video_path):
                            results["audio_processing"] = {
                                "processed_file_path": enhanced_video_path,
                                "status": "success"
                            }
                            # Update current working path
                            current_clip_path = enhanced_video_path
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
            
            # Process Captions if selected
            captioned_video_path = None
            if "Captions" in selected_features:
                try:
                    # Use final processed video path
                    final_video_path = current_clip_path
                    
                    # Process captions
                    transcriber = DjangoVideoTranscriber(
                        model_path="turbo",
                        video_path=final_video_path
                    )
                    
                    captioned_video_path = transcriber.process_video()
                    
                    results["captions"] = {
                        "processed_file_path": captioned_video_path,
                        "status": "success"
                    }
                    
                    # Update current working path
                    current_clip_path = captioned_video_path
                    logger.info(f"Updated path after captioning: {current_clip_path}")
                except Exception as e:
                    logger.error(f"Error in captioning: {e}")
                    results["captions"] = {"error": str(e)}
            
            # Upload the final processed file to S3
            final_processed_path = current_clip_path
            if final_processed_path and os.path.exists(final_processed_path):
                try:
                    # Create S3 key for the processed file
                    processed_filename = os.path.basename(final_processed_path)
                    processed_s3_key = f"processed/{processed_filename}"
                    
                    # Upload to S3
                    upload_result = s3_uploader.upload_file(
                        local_file_path=final_processed_path,
                        s3_key=processed_s3_key
                    )
                    
                    if upload_result["success"]:
                        # Add S3 URL and key to results
                        results["final_processed"] = {
                            "s3_url": upload_result["url"],
                            "s3_key": upload_result["key"],
                            "status": "success"
                        }
                    else:
                        results["final_processed"] = {
                            "error": upload_result["error"],
                            "status": "error"
                        }
                except Exception as e:
                    logger.error(f"Error uploading processed file to S3: {e}")
                    results["final_processed"] = {
                        "error": f"S3 upload error: {str(e)}",
                        "status": "error"
                    }
            
            # Clean up local files
            try:
                # Delete the original downloaded file
                if os.path.exists(local_clip_path):
                    os.remove(local_clip_path)
                
                # Delete intermediate processed files
                if upscaled_video_path and os.path.exists(upscaled_video_path):
                    os.remove(upscaled_video_path)
                
                if enhanced_video_path and os.path.exists(enhanced_video_path):
                    os.remove(enhanced_video_path)
                
                if captioned_video_path and os.path.exists(captioned_video_path):
                    os.remove(captioned_video_path)
                
                logger.info("Cleaned up local temporary files")
            except Exception as e:
                logger.warning(f"Error cleaning up local files: {e}")
                # Don't return an error if cleanup fails, just log it
            
            return JsonResponse({
                "message": "Processing completed successfully",
                "results": results
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
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_auth(request):
    if not request.user.is_authenticated:
        return Response({'error': 'User not authenticated'}, status=401)
    
    try:
        from .models import YouTubeAuth
        print(f"DEBUG: Checking YouTube auth for user {request.user.id}")
        youtube_auth = YouTubeAuth.objects.filter(user=request.user).first()
        has_youtube_auth = bool(youtube_auth and youtube_auth.credentials)
        print(f"DEBUG: YouTubeAuth exists: {bool(youtube_auth)}, has credentials: {has_youtube_auth}")
    except Exception as e:
        print(f"Error checking YouTube auth: {e}")
        has_youtube_auth = False
    
    return Response({'has_youtube_auth': has_youtube_auth})

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

from django.http import HttpResponse

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@csrf_exempt
def youtube_callback(request):
    """Handle callback from YouTube authorization"""
    # Get state from request parameters (not from session)
    state = request.GET.get('state')
    
    if not state or ':' not in state:
        return JsonResponse({'error': 'Invalid state format'}, status=400)
    
    # Extract user ID from state
    try:
        user_id, state_uuid = state.split(':', 1)
        user_id = int(user_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid state content'}, status=400)
    
    # Get authorization code from request
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'No authorization code'}, status=400)
    
    # Create flow instance
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'client_secret.json'),
        scopes=SCOPES,
        state=state  # Use the complete state from the request
    )
    flow.redirect_uri = request.build_absolute_uri('/api/youtube/callback/')
    
    # Exchange authorization code for access token
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
    except Exception as e:
        return JsonResponse({'error': f'Token exchange failed: {str(e)}'}, status=400)
    
    # Save credentials to database
    from .models import YouTubeAuth
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': f'User not found with ID: {user_id}'}, status=404)
    
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
    
    # Return HTML response instead of redirecting
    html_response = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Authorization Successful</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
            .success { color: #28a745; }
        </style>
    </head>
    <body>
        <h2 class="success">YouTube Authorization Successful!</h2>
        <p>You can now close this window and return to Channel-IQ.</p>
        <script>
            // Close window automatically after 3 seconds
            setTimeout(function() {
                window.close();
            }, 3000);
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_response)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_video(request):
    """Download video from S3 URL and upload to YouTube"""
    user = request.user
    
    # Check if user has valid YouTube credentials
    try:
        from .models import YouTubeAuth
        youtube_auth = YouTubeAuth.objects.get(user=user)
        if not youtube_auth.credentials:
            return Response({'error': 'YouTube authorization required'}, status=401)
    except YouTubeAuth.DoesNotExist:
        return Response({'error': 'YouTube authorization required'}, status=401)
    
    # Get video URL and metadata
    video_url = request.POST.get('video_url')
    s3_key = request.POST.get('s3_key', '')
    title = request.POST.get('title', 'My Video')
    description = request.POST.get('description', '')
    tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []
    
    if not video_url:
        return Response({'error': 'No video URL provided'}, status=400)
    
    # Download video from URL
    import tempfile
    import os
    import requests
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    temp_file.close()
    
    # For S3 URLs, we might use boto3 to get the file directly
    # But for this implementation, we'll use requests
    try:
        # Download the file from the URL
        if "amazonaws.com" in video_url and s3_key:
            # For S3 URLs, we can optionally use boto3 instead of requests
            # This is just an example of using boto3 directly, uncomment if needed
            """
            import boto3
            s3_client = boto3.client('s3')
            bucket_name = 'your-bucket-name'  # Extract from the URL or config
            s3_client.download_file(bucket_name, s3_key, temp_file.name)
            """
            # Otherwise, just use requests:
            response = requests.get(video_url, stream=True)
        else:
            # For local or other URLs
            response = requests.get(video_url, stream=True)
        
        response.raise_for_status()  # Raise exception for 4XX/5XX status codes
        
        # Write the content to the temporary file
        with open(temp_file.name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"DEBUG: Downloaded video from URL to: {temp_file.name}")
        print(f"DEBUG: File size: {os.path.getsize(temp_file.name)}")
        
        media = None
        try:
            # Use Google OAuth credentials
            from google.oauth2 import credentials as google_credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            
            # Get credentials from database
            creds_data = youtube_auth.credentials
            credentials = google_credentials.Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )
            
            # Create YouTube service
            youtube = build('youtube', 'v3', credentials=credentials)
            
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
            print(f"DEBUG: Upload successful, video ID: {response.get('id')}")
            
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
            import traceback
            print(f"DEBUG: YouTube upload error: {str(e)}")
            print(traceback.format_exc())
            return Response({'error': str(e)}, status=500)
            
        # Improved file cleanup section to replace in your upload_from_s3 function
        finally:
            # Close the MediaFileUpload object to release the file
            if media:
                try:
                    media.close()
                except:
                    pass
            
            # Wait longer before trying to delete the file on Windows
            import time
            import platform
            
            # Windows needs more time to release file handles
            if platform.system() == 'Windows':
                time.sleep(1.5)  # Longer wait time for Windows
            else:
                time.sleep(0.5)
            
            # Clean up temporary file with error handling and retry mechanism
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                        print(f"INFO: Successfully deleted temporary file: {temp_file.name}")
                        break  # Exit loop if deletion succeeds
                except Exception as e:
                    retry_count += 1
                    print(f"WARNING: Attempt {retry_count} - Could not delete temporary file: {str(e)}")
                    if retry_count < max_retries:
                        time.sleep(1.0)  # Wait before retrying
                    else:
                        print(f"ERROR: Failed to delete temporary file after {max_retries} attempts")
                        # On Windows, schedule the file for deletion on next reboot as a last resort
                        if platform.system() == 'Windows':
                            try:
                                import ctypes
                                MOVEFILE_DELAY_UNTIL_REBOOT = 4
                                ctypes.windll.kernel32.MoveFileExW(temp_file.name, None, MOVEFILE_DELAY_UNTIL_REBOOT)
                                print(f"INFO: File {temp_file.name} scheduled for deletion on next reboot")
                            except Exception as move_ex:
                                print(f"ERROR: Failed to schedule file for deletion: {str(move_ex)}")
    
    except requests.RequestException as e:
        print(f"ERROR: Failed to download video: {str(e)}")
        return Response({'error': f'Failed to download video: {str(e)}'}, status=500)
    
    except Exception as e:
        import traceback
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return Response({'error': str(e)}, status=500)
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
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_youtube_auth_url(request):
    """Generate and return a YouTube authorization URL with user ID embedded in state"""
    # Create OAuth 2.0 flow instance
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        os.path.join(settings.BASE_DIR, 'client_secret.json'),
        scopes=SCOPES
    )
    
    # Set redirect URI
    flow.redirect_uri = request.build_absolute_uri('/api/youtube/callback/')
    
    # Create a state that includes the user ID
    import uuid
    state = f"{request.user.id}:{uuid.uuid4().hex}"
    
    # Generate authorization URL with our custom state
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state
    )
    
    # Return the authorization URL
    return Response({'auth_url': authorization_url})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_youtube_seo(request):
    """Update YouTube video SEO metadata"""
    user = request.user
    
    # Check if user has valid YouTube credentials
    try:
        from .models import YouTubeAuth
        youtube_auth = YouTubeAuth.objects.get(user=user)
        if not youtube_auth.credentials:
            return Response({'error': 'YouTube authorization required'}, status=401)
    except YouTubeAuth.DoesNotExist:
        return Response({'error': 'YouTube authorization required'}, status=401)
    
    # Get video ID and metadata
    video_id = request.POST.get('video_id')
    title = request.POST.get('title')
    description = request.POST.get('description')
    tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []
    
    if not video_id:
        return Response({'error': 'No video ID provided'}, status=400)
    
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
        
        # First, get the current video details
        response = youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()
        
        if not response.get('items'):
            return Response({'error': 'Video not found or not accessible'}, status=404)
        
        # Prepare snippet with updated information
        snippet = response['items'][0]['snippet']
        
        # Update only the provided fields
        if title:
            snippet['title'] = title
        if description:
            snippet['description'] = description
        if tags:
            snippet['tags'] = tags
        
        # Update video metadata
        update_response = youtube.videos().update(
            part='snippet',
            body={
                'id': video_id,
                'snippet': snippet
            }
        ).execute()
        
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
        
        return Response({
            'success': True, 
            'message': 'Video SEO updated successfully',
            'video_id': video_id
        })
        
    except Exception as e:
        import traceback
        print(f"DEBUG: YouTube SEO update error: {str(e)}")
        print(traceback.format_exc())
        return Response({'error': str(e)}, status=500)