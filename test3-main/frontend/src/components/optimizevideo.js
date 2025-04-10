import React, { useEffect, useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { UserContext } from "./UserContext"; // Import User Context
import "./optimizevideo.css";
import { db } from "../Firebase"; // Import Firestore instance
import { doc, setDoc, serverTimestamp } from "firebase/firestore";

const OptimizeVideo = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Get user session

  const [videoPath, setVideoPath] = useState("");
  const [message, setMessage] = useState("");
  const [enhancementType, setEnhancementType] = useState("");

  useEffect(() => {
    if (!location.state) return;

    const { results = {}, selectedFeatures, localVideoPath, videoURL, videoTitle, videoId } = location.state;
    const userId = user?.uid;

    if (!userId) {
      console.error("❌ User ID is missing, cannot store data in Firestore.");
      return;
    }

    // ✅ Sanitize Video Title
    let sanitizedTitle = videoTitle
      ? videoTitle.replace(/[^\w\s]/gi, "").trim()
      : `video_${Date.now()}`;

    console.log("📌 Received Video Title:", videoTitle);
    console.log("📌 Sanitized Video Title:", sanitizedTitle);
    console.log("Received Results:", results);
    console.log("Selected Features:", selectedFeatures);

    let finalVideoPath = "";

    // First, check if we have an S3 upload result
    if (results.s3_upload && results.s3_upload.status === "success") {
      finalVideoPath = results.s3_upload.url;
      
      // Determine enhancement type based on which features were applied
      if (results.audio_processing && results.audio_processing.status === "success") {
        setEnhancementType("Audio Enhanced (S3)");
      } else if (results.video_upscaling && results.video_upscaling.status === "success") {
        setEnhancementType("Video Enhanced (S3)");
      } else {
        setEnhancementType("Original Video (S3)");
      }
      
      setMessage("✅ Video processing and upload completed successfully!");
    } else {
      // If no S3 URL, fall back to local paths
      const audioEnhancedPath = results.audio_processing?.processed_file_path;
      const videoEnhancedPath = results.video_upscaling?.processed_file_path;

      if (audioEnhancedPath) {
        // Extract filename from path and create local URL
        const filename = audioEnhancedPath.split("\\").pop();
        if (filename) {
          finalVideoPath = `http://127.0.0.1:8000/media/processed/${filename}`;
        }
        setEnhancementType("Audio Enhanced (Local)");
      } else if (videoEnhancedPath) {
        // Extract filename from path and create local URL
        const filename = videoEnhancedPath.split("\\").pop();
        if (filename) {
          finalVideoPath = `http://127.0.0.1:8000/media/processed/${filename}`;
        }
        setEnhancementType("Video Enhanced (Local)");
      } else {
        finalVideoPath = localVideoPath;
        setEnhancementType("Original Video (Local)");
      }

      setMessage(finalVideoPath ? "✅ Video processing completed successfully!" : "❌ No processed video available.");
    }

    setVideoPath(finalVideoPath);

    // ✅ Firestore Path
    const videoDocRef = doc(db, "users", userId, "videos", sanitizedTitle, "generate", "LongForm");

    // ✅ Storing all details inside "OptimizedVideo"
    setDoc(videoDocRef, {
      OptimizedVideo: {
        userId: userId,
        videoId: videoId || `vid_${Date.now()}`, // Generate a fallback if missing
        videoTitle: sanitizedTitle,
        originalVideoURL: videoURL || "Unknown",
        processedVideoURL: finalVideoPath || "Unknown",
        processedURL: results?.s3_upload?.url || null, // Adding processedURL
        s3FinalURL: results?.s3_upload?.url || null,
        s3Key: results?.s3_upload?.key || null,
        localPath: localVideoPath || null,
        selectedFeatures: selectedFeatures || [],
        enhancementType: enhancementType,
        status: results?.s3_upload?.status || results?.audio_processing?.status || "failed",
        timestamp: serverTimestamp(),
      }
    }, { merge: true })
      .then(() => console.log("✅ OptimizedVideo data saved successfully!"))
      .catch((error) => console.error("❌ Error saving OptimizedVideo data:", error));

  }, [location.state, user]); // Added dependency array

  const handleCompare = () => {
    if (!location.state) return;

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