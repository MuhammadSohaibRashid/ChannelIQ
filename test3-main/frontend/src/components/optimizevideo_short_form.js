import React, { useEffect, useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { UserContext } from "./UserContext"; // Import User Context
import "./optimizevideo.css";

const Optimizevideo_shortform = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // User session
  const [videoPath, setVideoPath] = useState("");
  const [message, setMessage] = useState("");
  const [enhancementType, setEnhancementType] = useState("");
  const [isCaptionAdded, setIsCaptionAdded] = useState(false); // New state for captions

  useEffect(() => {
    if (location.state) {
      const { results = {}, selectedFeatures, selectedClip } = location.state;
      console.log("Received Results:", results);

      // Extract paths for audio, video, and captions
      const audioEnhancedPath = results.audio_processing?.processed_file_path;
      const videoEnhancedPath = results.video_upscaling?.processed_file_path;
      const captionedVideoPath = results.captions?.processed_file_path; // Captioned video path

      let selectedPath = "";
      let enhancementType = "";

      // Determine which path to use based on processing order
      if (captionedVideoPath) {
        selectedPath = captionedVideoPath;
        enhancementType = "Captions Added";
        setIsCaptionAdded(true);
      } else if (audioEnhancedPath) {
        selectedPath = audioEnhancedPath;
        enhancementType = "Audio Enhanced";
      } else if (videoEnhancedPath) {
        selectedPath = videoEnhancedPath;
        enhancementType = "Video Enhanced";
      }

      // Set the video path and enhancement type
      if (selectedPath) {
        const filename = selectedPath.split("\\").pop();
        if (filename) {
          setVideoPath(`http://127.0.0.1:8000/media/processed/${filename}`);
          setMessage("Video processing completed successfully!");
          setEnhancementType(enhancementType);
        }
      } else {
        setMessage("No processed video available.");
      }
    }
  }, [location.state]);

  const handleCompare = () => {
    const { results, selectedFeatures, selectedClip } = location.state;

    // Extract filename from the URL path
    const originalFilename = selectedClip.split("/").pop();

    navigate("/comparison", {
      state: {
        results: results,
        selectedFeatures,
        videoURL: null,
        localVideoPath: `\\media\\videos\\${originalFilename}`,
        seoData: null,
      },
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
          <h1>Optimized Short-form Video</h1>
          <p>{message}</p>
        </header>

        <div className="enhancement-info">
          <span className="enhancement-badge">{enhancementType}</span>
          {isCaptionAdded && ( // Display captions badge if captions were added
            <span className="enhancement-badge captions-badge">Captions</span>
          )}
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

export default Optimizevideo_shortform;
