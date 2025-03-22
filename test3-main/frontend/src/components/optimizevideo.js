import React, { useEffect, useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { UserContext } from "./UserContext"; // Import User Context
import "./optimizevideo.css";

const OptimizeVideo = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Get user session

  const [videoPath, setVideoPath] = useState("");
  const [message, setMessage] = useState("");
  const [enhancementType, setEnhancementType] = useState("");

  useEffect(() => {
    if (location.state) {
      const { results = {}, selectedFeatures, localVideoPath, videoURL } = location.state;
      console.log("Received Results:", results);
      console.log("Selected Features:", selectedFeatures);

      // First, check if we have an S3 upload result
      if (results.s3_upload && results.s3_upload.status === "success") {
        setVideoPath(results.s3_upload.url);
        
        // Determine enhancement type based on which features were applied
        if (results.audio_processing && results.audio_processing.status === "success") {
          setEnhancementType("Audio Enhanced (S3)");
        } else if (results.video_upscaling && results.video_upscaling.status === "success") {
          setEnhancementType("Video Enhanced (S3)");
        } else {
          setEnhancementType("Original Video (S3)");
        }
        
        setMessage("Video processing and upload completed successfully!");
        return;
      }

      // If no S3 URL, fall back to local paths
      const audioEnhancedPath = results.audio_processing?.processed_file_path;
      const videoEnhancedPath = results.video_upscaling?.processed_file_path;

      let selectedPath = "";
      if (audioEnhancedPath) {
        selectedPath = audioEnhancedPath;
        setEnhancementType("Audio Enhanced (Local)");
      } else if (videoEnhancedPath) {
        selectedPath = videoEnhancedPath;
        setEnhancementType("Video Enhanced (Local)");
      } else {
        selectedPath = localVideoPath;
        setEnhancementType("Original Video (Local)");
      }

      if (selectedPath) {
        // Check if it's already a URL
        if (selectedPath.startsWith('http')) {
          setVideoPath(selectedPath);
        } else {
          // Extract filename from path and create local URL
          const filename = selectedPath.split("\\").pop();
          if (filename) {
            setVideoPath(`http://127.0.0.1:8000/media/processed/${filename}`);
          }
        }
        setMessage("Video processing completed successfully!");
      } else {
        setMessage("No processed video available.");
      }
    }
  }, [location.state]);

  const handleCompare = () => {
    const { results, selectedFeatures, videoURL, localVideoPath } = location.state;

    navigate("/comparison", {
      state: {
        results,
        selectedFeatures,
        videoURL,
        localVideoPath,
        seoData: null
      }
    });
  };

  return (
    <div className="clipping-app">
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

      <div className="optimized-video-page">
        <header className="page-header">
          <h1>Optimized Video Output</h1>
          <p>{message}</p>
        </header>

        <div className="enhancement-info">
          <span className="enhancement-badge">
            {enhancementType}
          </span>
        </div>

        <div className="video-output">
          {videoPath ? (
            <>
              <video className="optimized-video" controls src={videoPath}>
                Your browser does not support the video tag.
              </video>
              <div className="video-info">
                <div className="action-buttons">
                  <button className="comparison-btn" onClick={handleCompare}>
                    Compare Results
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="no-video">
              <p>No optimized video available.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OptimizeVideo;