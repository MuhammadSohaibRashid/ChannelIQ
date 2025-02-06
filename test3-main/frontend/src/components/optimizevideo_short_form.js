import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./optimizevideo.css";

const Optimizevideo_shortform = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [videoPath, setVideoPath] = useState("");
  const [message, setMessage] = useState("");
  const [enhancementType, setEnhancementType] = useState("");
  let videoURL, results, localVideoPath, selectedFeatures;
  useEffect(() => {
    if (location.state) {
      const { results = {}, selectedFeatures, selectedClip } = location.state;
      console.log("Received Results:", results);
      const audioEnhancedPath = results.audio_processing?.processed_file_path;
      const videoEnhancedPath = results.video_upscaling?.processed_file_path;

      let selectedPath = "";
      if (audioEnhancedPath) {
        selectedPath = audioEnhancedPath;
        setEnhancementType("Audio Enhanced");
      } else if (videoEnhancedPath) {
        selectedPath = videoEnhancedPath;
        setEnhancementType("Video Enhanced");
      } 

      if (selectedPath) {
        const filename = selectedPath.split('\\').pop();
        if (filename) {
          setVideoPath(`http://127.0.0.1:8000/media/processed/${filename}`);
          setMessage("Video processing completed successfully!");
        }
      } else {
        setMessage("No processed video available.");
      }
    }
  }, [location.state]);

 const handleCompare = () => {
    const { results, selectedFeatures, selectedClip } = location.state;

    // Convert the HTTP URL back to local file path format
    const localPath = selectedClip.replace(
      'http://127.0.0.1:8000/media/processed/',
      'C:\\Users\\aqiba\\Desktop\\test3-main\\test3-main\\backend\\media\\processed\\'
    );

    // Filter out SEO data from results


    const clipData = Object.values(results)[0] || {};

    // Navigate with unnested data
    navigate('/comparison', {
      state: {
        results: clipData, // Send the unnested data directly
        selectedFeatures,
        videoURL: null,
        localVideoPath: localPath,
        seoData: null
      }
    });
  };
  return (
    <div className="clipping-app">
      <header className="header">
        <h1 className="logo">
          <span className="bold">Channel-</span>
          <span className="highlight">IQ</span>
        </h1>
        <nav className="nav">
          <a href="#clipper">Clipper</a>
          <a href="#pricing">Pricing</a>
          <button className="sign-in">Sign in</button>
          <button className="sign-up">Sign up</button>
          <button
            className="home-button"
            onClick={() => navigate('/clipper')}
          >
            Home
          </button>
        </nav>
      </header>

      <div className="optimized-video-page">
        <header className="page-header">
          <h1>Optimized Short-form Video</h1>
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

export default Optimizevideo_shortform;