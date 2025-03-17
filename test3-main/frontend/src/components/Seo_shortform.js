import React, { useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { UserContext } from "./UserContext"; // Import User Context
import "./Seo_shortform.css";

function Seo_shortform({ videoThumbnail }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Get user session
  const { message, results, selectedFeatures, selectedClip } = location.state || {};
  const [seoMessage, setSeoMessage] = useState(message || "No SEO data received.");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  const getVideoUrl = () => {
    if (selectedFeatures.length === 1 && selectedFeatures.includes("SEO")) {
      return selectedClip;
    }

    if (results?.audio_processing?.processed_file_path) {
      const fileName = results.audio_processing.processed_file_path.split("\\").pop();
      return `http://127.0.0.1:8000/media/processed/${fileName}`;
    }

    if (results?.video_upscaling?.processed_file_path) {
      const fileName = results.video_upscaling.processed_file_path.split("\\").pop();
      return `http://127.0.0.1:8000/media/processed/${fileName}`;
    }

    if (results?.captions?.processed_file_path) {
      const fileName = results.captions.processed_file_path.split("\\").pop();
      return `http://127.0.0.1:8000/media/processed/${fileName}`;
    }

    return selectedClip;
  };

  const handleCompare = () => {
    const originalFilename = selectedClip.split("/").pop();

    navigate("/comparison", {
      state: {
        results: results,
        selectedFeatures,
        videoURL: null,
        localVideoPath: `\\media\\videos\\${originalFilename}`,
        seoData: null
      }
    });
  };

  const handleUploadToYouTube = async () => {
    if (!user) {
      setUploadStatus({
        success: false,
        message: "You must be logged in to upload to YouTube"
      });
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      // Create a FormData object to send the video file and metadata
      const formData = new FormData();
      
      // Get the video file from the URL
      const videoUrl = getVideoUrl();
      const response = await fetch(videoUrl);
      const blob = await response.blob();
      
      // Create a File object from the blob
      const fileName = videoUrl.split("/").pop();
      const videoFile = new File([blob], fileName, { type: "video/mp4" });
      
      // Add the video file to the form data
      formData.append("video", videoFile);
      
      // Add the SEO data to the form data
      formData.append("title", results?.seo?.title || "My Video");
      formData.append("description", results?.seo?.description || "");
      formData.append("tags", results?.seo?.tags?.join(",") || "");
      
      // Make the API request to upload the video
      const uploadResponse = await fetch("http://127.0.0.1:8000/api/youtube/upload/", {
        method: "POST",
        headers: {
          Authorization: `Token ${localStorage.getItem("authToken")}`,
        },
        body: formData,
      });
      
      const data = await uploadResponse.json();
      
      if (data.success) {
        setUploadStatus({
          success: true,
          message: `Video uploaded successfully! Video ID: ${data.video_id}`,
          videoId: data.video_id
        });
      } else {
        setUploadStatus({
          success: false,
          message: data.error || "Failed to upload video"
        });
      }
    } catch (error) {
      console.error("Upload error:", error);
      setUploadStatus({
        success: false,
        message: "An error occurred during upload"
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="seo-app">
      {/* Navbar with User Session */}
      <header className="header">
        <h1 className="logo" onClick={() => navigate("/")}>
          <span className="bold">Channel-</span>
          <span className="highlight">IQ</span>
        </h1>

        <nav className="nav">
          {user ? (
            <div className="user-info">
              <img src={user.picture} alt="User" className="user-avatar" />
              <span className="username">{user.name}</span>
              <button className="logout-btn" onClick={logout}>Logout</button>
            </div>
          ) : (
            <button className="login-btn" onClick={() => navigate("/login")}>
              Login
            </button>
          )}
          <button className="home-button" onClick={() => navigate("/clipper")}>
            Back to Clipper
          </button>
        </nav>
      </header>

      <main className="main-content">
        <button className="clipper-btn" onClick={() => navigate("/clipper")}>
          Go to Clipper
        </button>

        <div className="clip-section">
          <div className="media-preview">
            <video className="preview-video" controls>
              <source src={getVideoUrl()} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>

          <div className="customize-clip">
            <div className="seo-data">
              <div className="seo-box">
                <h2>Title</h2>
                <p>{results?.seo?.title || "No title available."}</p>
              </div>
              <div className="seo-box">
                <h2>Description</h2>
                <p>{results?.seo?.description || "No description available."}</p>
              </div>
              <div className="seo-box">
                <h2>Keywords</h2>
                <p>{results?.seo?.keywords?.join(", ") || "No keywords available."}</p>
              </div>
              <div className="seo-box">
                <h2>Tags</h2>
                <p>{results?.seo?.tags?.join(", ") || "No tags available."}</p>
              </div>
            </div>

            <div className="action-buttons">
              {(selectedFeatures?.includes("Noise Reduction") ||
                selectedFeatures?.includes("Video Quality") ||
                selectedFeatures?.includes("Captions")) && (
                <button className="comparison-btn" onClick={handleCompare}>
                  Compare Results
                </button>
              )}
              
              {/* YouTube Upload Button */}
              <button 
                className={`youtube-upload-btn ${uploading ? 'uploading' : ''}`}
                onClick={handleUploadToYouTube}
                disabled={uploading}
              >
                {uploading ? "Uploading..." : "Upload to YouTube"}
              </button>
            </div>

            {/* Upload Status Message */}
            {uploadStatus && (
              <div className={`upload-status ${uploadStatus.success ? 'success' : 'error'}`}>
                <p>{uploadStatus.message}</p>
                {uploadStatus.success && uploadStatus.videoId && (
                  <a 
                    href={`https://www.youtube.com/watch?v=${uploadStatus.videoId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="view-video-link"
                  >
                    View on YouTube
                  </a>
                )}
              </div>
            )}

            {/* YouTube Authorization Message */}
            {user && !uploading && !uploadStatus && (
              <div className="youtube-auth-note">
                <p>
                  <strong>Note:</strong> To upload videos to YouTube, you need to authorize Channel-IQ to 
                  access your YouTube account. 
                  {!user.has_youtube_auth && (
                    <a href="/api/youtube/authorize/" className="auth-link">
                      Authorize YouTube
                    </a>
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default Seo_shortform;