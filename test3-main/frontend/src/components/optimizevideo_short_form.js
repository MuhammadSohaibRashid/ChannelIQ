import React, { useEffect, useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { UserContext } from "./UserContext"; // Import User Context
import "./optimizevideo.css";
import { doc, setDoc, serverTimestamp, getDocs, collection } from "firebase/firestore"; // Firestore imports
import { db } from "../Firebase"; // Make sure the Firebase config is correctly imported

const Optimizevideo_shortform = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // User session
  const [videoPath, setVideoPath] = useState("");
  const [message, setMessage] = useState("");
  const [enhancementType, setEnhancementType] = useState("");
  const [isCaptionAdded, setIsCaptionAdded] = useState(false); // New state for captions
  const [originalClip, setOriginalClip] = useState(null);
  const [videoTitle, setVideoTitle] = useState(""); // Added state for video title

  useEffect(() => {
    if (location.state) {
      const { results = {}, selectedFeatures, selectedClip, videoTitle } = location.state;
      console.log("Received Results:", results);
      setOriginalClip(selectedClip);
      setVideoTitle(videoTitle || "Untitled Video");

      // Check if we have the final processed S3 URL
      if (results.final_processed && results.final_processed.s3_url) {
        setVideoPath(results.final_processed.s3_url);
        
        // Determine enhancement types based on selected features
        let enhancementLabel = "";
        
        if (selectedFeatures.includes("Video Quality")) {
          enhancementLabel = "Video Enhanced";
        }
        
        if (selectedFeatures.includes("Noise Reduction")) {
          enhancementLabel = enhancementLabel ? "Audio & Video Enhanced" : "Audio Enhanced";
        }
        
        if (selectedFeatures.includes("Captions")) {
          setIsCaptionAdded(true);
          enhancementLabel = enhancementLabel ? `${enhancementLabel}, Captions Added` : "Captions Added";
        }
        
        setEnhancementType(enhancementLabel);
        setMessage("Your short-form video is enhanced and good to go!");
        
        // Save to Firebase
        saveOptimizationDetails({
          processedVideoURL: results.final_processed.s3_url,
          originalVideoURL: selectedClip,
          enhancementType: enhancementLabel,
          selectedFeatures,
          videoTitle,
        });
      } else {
        // Fallback to individual processes if final isn't available
        const audioEnhancedPath = results.audio_processing?.processed_file_path;
        const videoEnhancedPath = results.video_upscaling?.processed_file_path;
        const captionedVideoPath = results.captions?.processed_file_path;

        // Check for S3 URLs in individual processes
        const audioS3Url = results.audio_processing?.s3_url;
        const videoS3Url = results.video_upscaling?.s3_url;
        const captionsS3Url = results.captions?.s3_url;

        let selectedPath = "";
        let enhancementType = "";

        // Prioritize S3 URLs if available
        if (captionsS3Url) {
          selectedPath = captionsS3Url;
          enhancementType = "Captions Added";
          setIsCaptionAdded(true);
        } else if (audioS3Url) {
          selectedPath = audioS3Url;
          enhancementType = "Audio Enhanced";
        } else if (videoS3Url) {
          selectedPath = videoS3Url;
          enhancementType = "Video Enhanced";
        } 
        // Fallback to local paths if no S3 URLs
        else if (captionedVideoPath) {
          const filename = captionedVideoPath.split(/[\\/]/).pop();
          selectedPath = `http://127.0.0.1:8000/media/processed/${filename}`;
          enhancementType = "Captions Added";
          setIsCaptionAdded(true);
        } else if (audioEnhancedPath) {
          const filename = audioEnhancedPath.split(/[\\/]/).pop();
          selectedPath = `http://127.0.0.1:8000/media/processed/${filename}`;
          enhancementType = "Audio Enhanced";
        } else if (videoEnhancedPath) {
          const filename = videoEnhancedPath.split(/[\\/]/).pop();
          selectedPath = `http://127.0.0.1:8000/media/processed/${filename}`;
          enhancementType = "Video Enhanced";
        }

        if (selectedPath) {
          setVideoPath(selectedPath);
          setMessage("Your short-form video is enhanced and good to go!");
          setEnhancementType(enhancementType);
          
          // Save to Firebase
          saveOptimizationDetails({
            processedVideoURL: selectedPath,
            originalVideoURL: selectedClip,
            enhancementType: enhancementType,
            selectedFeatures,
            videoTitle,
          });
        } else {
          setMessage("No processed video available.");
        }
      }
    }
  }, [location.state]);

  // Function to store details in Firestore
  const saveOptimizationDetails = async ({
    processedVideoURL,
    originalVideoURL,
    enhancementType,
    selectedFeatures,
    videoTitle, // Accept videoTitle as a parameter
  }) => {
    console.log("🔄 saveOptimizationDetails called");

    if (!user) {
      console.log("❌ User not logged in. Cannot save video details.");
      return;
    }

    try {
      console.log("🔍 Fetching videos for user:", user.uid);
      const videosRef = collection(db, "users", user.uid, "videos");
      const querySnapshot = await getDocs(videosRef);

      // ✅ Apply new title logic
      let sanitizedTitle = videoTitle
        ? videoTitle.replace(/[^\w\s]/gi, "").trim()
        : `video_${Date.now()}`; // Fallback if undefined

      let originalTitle = videoTitle || "Unknown Video";

      console.log("📌 Received Video Title:", videoTitle);
      console.log("📌 Step 1: Initial Sanitized Title:", sanitizedTitle);

      // Fetch title from Firestore if not available
      if (!videoTitle) {
        querySnapshot.forEach((doc) => {
          const videoData = doc.data();
          console.log("📌 Video Data from Firestore:", videoData);

          if (videoData.title) {
            let title = videoData.title.replace(/[^\w\s]/gi, "").trim();
            console.log("✅ Found and Sanitized Title from Firestore:", title);

            if (!sanitizedTitle) {
              sanitizedTitle = title;
              originalTitle = videoData.title;
              console.log("🟢 Step 2: Updated Sanitized Title:", sanitizedTitle);
              console.log("🟢 Step 3: Updated Original Title:", originalTitle);
            }
          }
        });
      }

      // Final fallback if title is still unavailable
      if (!sanitizedTitle) {
        console.log("⚠️ No matching video found. Using fallback.");
        sanitizedTitle = `video_${Date.now()}`;
        originalTitle = "Unknown Video";
      }

      console.log("📌 Final Sanitized Video Title:", sanitizedTitle);
      console.log("✅ Firestore Path:", `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`);

      // Save to Firestore (Ensure the correct document path is used)
      const clipDocRef = doc(db, `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`);

      await setDoc(
        clipDocRef,
        {
          processedVideoURL,
          originalVideoURL,
          enhancementType,
          selectedFeatures,
          timestamp: serverTimestamp(),
          videoTitle: originalTitle, // Save actual video title
        },
        { merge: true }
      );

      console.log("✅ Video details saved successfully in Firestore!");
    } catch (error) {
      console.error("🔥 Error saving video details to Firestore:", error);
    }
  };

  const handleCompare = () => {
    const { results, selectedFeatures } = location.state;

    navigate("/comparison", {
      state: {
        results: results,
        selectedFeatures,
        originalClip: originalClip,
        processedVideo: videoPath,
        seoData: results.seo || null,
      },
    });
  };
// Handle video download
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
          <h1>Optimized Short-form Video</h1>
          <p>{message}</p>
        </header>

        <div className="enhancement-info">
          <span className="enhancement-badge">{enhancementType}</span>
          {isCaptionAdded && !enhancementType.includes("Captions") && (
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
                  <button className="download-btn" onClick={handleDownload}>
                    Download Video
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