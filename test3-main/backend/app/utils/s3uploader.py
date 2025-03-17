import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Uploader:
    """
    Utility class for handling file uploads to Amazon S3 with user-specific paths.
    """
    
    def __init__(self, aws_access_key_id, aws_secret_access_key, bucket_name, region=None):
        """
        Initialize the S3Uploader with AWS credentials and bucket information.
        
        Args:
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            bucket_name: S3 bucket name to upload to
            region: AWS region (optional)
        """
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.bucket_name = bucket_name
        self.region = region
        
        # Create S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region
        )
    
    def file_exists_in_s3(self, s3_key):
        """
        Check if a file exists in the S3 bucket.
        
        Args:
            s3_key: The key (path) of the file in S3
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            # Re-raise if it's not a 404 error
            raise
    
    def get_s3_url(self, s3_key):
        """
        Get the URL for a file in S3.
        
        Args:
            s3_key: The key (path) of the file in S3
            
        Returns:
            str: URL to the file in S3
        """
        return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
    
    def upload_file(self, local_file_path, s3_key, make_public=False):
        """
        Upload a file to S3.
        
        Args:
            local_file_path: Path to the file on local storage
            s3_key: The key (path) where the file will be stored in S3
            make_public: Whether to make the file publicly accessible
            
        Returns:
            dict: Result containing success status and file URL if successful
        """
        if not os.path.exists(local_file_path):
            return {
                "success": False,
                "error": f"Local file not found: {local_file_path}"
            }
        
        try:
            extra_args = {}
            if make_public:
                extra_args['ACL'] = 'public-read'
            
            logger.debug(f"Uploading file to S3 bucket: {self.bucket_name}, key: {s3_key}")
            self.s3_client.upload_file(
                local_file_path, 
                self.bucket_name, 
                s3_key,
                ExtraArgs=extra_args
            )
            
            return {
                "success": True,
                "url": self.get_s3_url(s3_key),
                "key": s3_key
            }
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {str(e)}")
            return {
                "success": False,
                "error": f"S3 upload failed: {str(e)}"
            }
        except Exception as e:
            logger.exception("Unexpected error during S3 upload")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_user_video_key(self, user_id, video_id, extension="mp4"):
        """
        Generate an S3 key for a user-specific video.
        
        Args:
            user_id: User identifier
            video_id: Video identifier
            extension: File extension (default: mp4)
            
        Returns:
            str: S3 key for the user's video
        """
        return f"users/{user_id}/videos/{video_id}.{extension}"
    
    def list_user_videos(self, user_id):
        """
        List all videos for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            list: List of video objects (keys and URLs)
        """
        try:
            prefix = f"users/{user_id}/videos/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            videos = []
            if 'Contents' in response:
                for item in response['Contents']:
                    key = item['Key']
                    # Extract video_id from the key
                    video_id = os.path.basename(key).split('.')[0]
                    videos.append({
                        'key': key,
                        'video_id': video_id,
                        'url': self.get_s3_url(key),
                        'size': item['Size'],
                        'last_modified': item['LastModified']
                    })
            
            return {
                "success": True,
                "videos": videos
            }
            
        except ClientError as e:
            logger.error(f"Error listing user videos: {str(e)}")
            return {
                "success": False,
                "error": f"Error listing videos: {str(e)}"
            }
    
    def delete_user_video(self, user_id, video_id):
        """
        Delete a specific user's video.
        
        Args:
            user_id: User identifier
            video_id: Video identifier
            
        Returns:
            dict: Result containing success status
        """
        s3_key = self.get_user_video_key(user_id, video_id)
        return self.delete_file(s3_key)
    
    def delete_file(self, s3_key):
        """
        Delete a file from S3.
        
        Args:
            s3_key: The key (path) of the file in S3
            
        Returns:
            dict: Result containing success status
        """
        try:
            logger.debug(f"Deleting file from S3 bucket: {self.bucket_name}, key: {s3_key}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            
            return {
                "success": True
            }
            
        except ClientError as e:
            logger.error(f"S3 delete failed: {str(e)}")
            return {
                "success": False,
                "error": f"S3 delete failed: {str(e)}"
            }