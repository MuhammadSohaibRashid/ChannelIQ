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
  const [videoTitle, setVideoTitle] = useState(""); // Added state for video title
  const [videoPath, setVideoPath] = useState("");
  const [message, setMessage] = useState("");
  const [enhancementType, setEnhancementType] = useState("");

  useEffect(() => {
      // Debug the incoming data from previous page
      console.log("📌 Received location state:", location.state);
      
      if (!location.state) {
        console.warn("⚠️ No location state received, nothing to process");
        return;
      }
      
      const { 
        results = {}, 
        selectedFeatures = [], 
        localVideoPath, 
        videoURL, 
        videoTitle, 
        videoId 
      } = location.state;
      
      // More debugging for the specific fields we're interested in
      console.log("📌 Results object:", results);
      console.log("📌 Selected Features:", selectedFeatures);
      console.log("📌 Original Video Title:", videoTitle);
      
      const userId = user?.uid;
      
      if (!userId) {
        console.error("❌ User ID is missing, cannot store data in Firestore.");
        return;
      }
      
      // Sanitize Video Title
      let sanitizedTitle = videoTitle
        ? videoTitle.replace(/[^\w\s-]/gi, "").trim()
        : `video_${Date.now()}`;
      
      console.log("📌 Sanitized Video Title:", sanitizedTitle);
      
      // Extract processing details
      const audioProcessing = results.audio_processing || {};
      const videoUpscaling = results.video_upscaling || {};
      const s3Upload = results.s3_upload || {};
      const emailNotification = results.email_notification || {};
      
      // Determine the final URL to use and enhancement type
      let finalVideoPath = "";
      let enhancementType = "Original Video";
      
      // First, check if we have an S3 upload result
      if (s3Upload.status === "success" && s3Upload.url) {
        finalVideoPath = s3Upload.url;
        
        // Determine enhancement type based on selected features
        if (selectedFeatures.includes('Noise Reduction') && selectedFeatures.includes('Video Quality')) {
          enhancementType = "Audio & Video Enhanced (S3)";
        } else if (selectedFeatures.includes('Noise Reduction')) {
          enhancementType = "Audio Enhanced (S3)";
        } else if (selectedFeatures.includes('Video Quality')) {
          enhancementType = "Video Quality Enhanced (S3)";
        } else {
          enhancementType = "Original Video (S3)";
        }
        
        setMessage("✅ Video processing and upload completed successfully!");
      } else {
        // Check for video upscaling results
        if (selectedFeatures.includes('Video Quality') && videoUpscaling.status === "success") {
          if (videoUpscaling.s3_processed_file_path) {
            finalVideoPath = videoUpscaling.s3_processed_file_path;
            enhancementType = "Video Quality Enhanced (S3)";
          } else if (videoUpscaling.processed_file_path) {
            // Extract filename from path and create local URL
            const filename = videoUpscaling.processed_file_path.split("\\").pop();
            if (filename) {
              finalVideoPath = `http://127.0.0.1:8000/media/processed/${filename}`;
            }
            enhancementType = "Video Quality Enhanced (Local)";
          }
          
          setMessage("✅ Video quality enhancement completed successfully!");
        } 
        // Check for audio processing results
        else if (selectedFeatures.includes('Noise Reduction') && audioProcessing.status === "success") {
          if (audioProcessing.s3_processed_file_path) {
            finalVideoPath = audioProcessing.s3_processed_file_path;
            enhancementType = "Audio Enhanced (S3)";
          } else if (audioProcessing.processed_file_path) {
            // Extract filename from path and create local URL
            const filename = audioProcessing.processed_file_path.split("\\").pop();
            if (filename) {
              finalVideoPath = `http://127.0.0.1:8000/media/processed/${filename}`;
            }
            enhancementType = "Audio Enhanced (Local)";
          }
          
          setMessage("✅ Audio processing completed successfully!");
        } else {
          // Fall back to original video
          finalVideoPath = videoURL || localVideoPath || "";
          enhancementType = "Original Video";
          
          setMessage(finalVideoPath ? "✅ Using original video" : "❌ No video available.");
        }
      }
      
      setVideoPath(finalVideoPath);
      setVideoTitle(sanitizedTitle); // Set the video title for download functionality
      setEnhancementType(enhancementType);
      
      // Create simplified data object with only necessary fields
      const simplifiedData = {
        userId,
        videoId: videoId || `vid_${Date.now()}`,
        videoTitle: sanitizedTitle,
        originalVideoURL: videoURL || "Unknown",
        processedVideoURL: finalVideoPath || "Unknown",
        selectedFeatures,
        enhancementType,
        status: s3Upload.status || audioProcessing.status || videoUpscaling.status || "unknown",
        timestamp: serverTimestamp(),
      };
      
      // Add audio processing details if selected or available
      if (selectedFeatures.includes('Noise Reduction') || Object.keys(audioProcessing).length > 0) {
        simplifiedData.audioProcessing = {
          status: audioProcessing.status || "unknown",
          processed_file_path: audioProcessing.processed_file_path || null,
          s3_processed_file_path: audioProcessing.s3_processed_file_path || null
        };
      }
      
      // Add video upscaling details if selected or available
      if (selectedFeatures.includes('Video Quality') || Object.keys(videoUpscaling).length > 0) {
        simplifiedData.videoUpscaling = {
          status: videoUpscaling.status || "unknown",
          processed_file_path: videoUpscaling.processed_file_path || null,
          s3_processed_file_path: videoUpscaling.s3_processed_file_path || null
        };
      }
      
      // Add S3 details
      simplifiedData.s3 = {
        key: s3Upload.key || null,
        url: s3Upload.url || null,
        status: s3Upload.status || "unknown"
      };
      
      // Add email notification details
      simplifiedData.emailNotification = {
        email: emailNotification.email || null,
        status: emailNotification.status || "unknown"
      };
      
      console.log("📌 Simplified data to be saved:", simplifiedData);
      
      // Firestore path and save
      const videoDocRef = doc(db, "users", userId, "videos", sanitizedTitle, "generate", "LongForm");
      
      setDoc(videoDocRef, {
        OptimizedVid: simplifiedData
      })
        .then(() => console.log("✅ Video processing data saved successfully!"))
        .catch((error) => console.error("❌ Error saving video processing data:", error));
      
    }, [location.state, user]);

  const handleCompare = () => {
    if (!location.state) return;
    const { results, selectedFeatures, videoURL, localVideoPath, videoId } = location.state;

    navigate("/comparison", {
      state: {
        results,
        selectedFeatures,
        videoURL,
        localVideoPath,
        s3Key: results.s3_upload?.key || null, // Add S3 key
        processedS3Url: videoPath, // The processed video URL (already set from S3)
        videoId, // Add video ID if available
        seoData: null
      }
    });
  };

  const handleDownload = () => {
    if (videoPath) {
      // Create a temporary anchor element
      const link = document.createElement("a");
      link.href = videoPath;
      
      // Set the download attribute and suggested filename
      link.download = `${videoTitle.replace(/[^\w\s]/gi, "_")}_optimized.mp4`;
      
      // Programmatically click the link to trigger download
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      document.body.removeChild(link);
    }
  };

  return (
    <div className="clipping-app">
      {/* Navbar with User Session */}
       {/* Header */}
       <header className="dashboard-header">
  <div className="logo-container" onClick={() => navigate("/")}>
    <h1 className="logo">
      <span className="logo-bold">Channel-</span>
      <span className="logo-highlight">IQ</span>
    </h1>
  </div>

  <div className="header-right">
    <a 
      className="nav-link" 
      href="/terms" // or use navigate("/terms") if you're using React Router
      style={{ marginRight: '1rem', textDecoration: 'none', color: 'var(--color-text)', fontWeight: 500 }}
    >
      Terms & Services
    </a>
    <a 
        className="nav-link" 
        href="/videos" // Add this new link
        style={{ marginRight: '1rem', textDecoration: 'none', color: 'var(--color-text)', fontWeight: 500 }}
    >
        Videos
    </a>

    {user ? (
      <div className="user-profile">
        <img src={user.picture} alt="User" className="user-avatar" />
        <span className="username">{user.name}</span>
        <button className="logout-button" onClick={logout}>Logout</button>
      </div>
    ) : (
      <button className="login-button" onClick={() => navigate("/login")}>
        Login
      </button>
    )}
  </div>
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
                  <button className="comparison-btn-lf" onClick={handleCompare}>
                    Compare Results
                  </button>
                  <button className="download-btn" onClick={handleDownload}>
                    Download
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