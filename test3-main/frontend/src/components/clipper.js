import React, { useState, useContext } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { fetchVideoMetadata, downloadAndUploadVideo } from "../axios-use/api";
import "./clipper.css";
import { UserContext } from "./UserContext"; // Import User Context
import { db } from "../Firebase";  // Import Firebase Firestore
import { getDocs,setDoc,collection, addDoc, updateDoc, doc,serverTimestamp} from "firebase/firestore";
import {  query, where } from "firebase/firestore";
import { v4 as uuidv4 } from "uuid"; // Import UUID for unique IDs

import VideoDashboard from "./videoDashboard";


function Clipper() {
  const { user, logout } = useContext(UserContext);
  const [videoURL, setVideoURL] = useState("");
  const [videoData, setVideoData] = useState(null);
  const [loading, setLoading] = useState(false); // Initialize loading as false
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [optimizationType, setOptimizationType] = useState("");
  const [clipLength, setClipLength] = useState("90");
  const [clipCount, setClipCount] = useState(1);
  const [selectedFeatures, setSelectedFeatures] = useState([]);
  const [showDashboard, setShowDashboard] = useState(true);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [loadingUser, setLoadingUser] = useState(false); // Initialize loadingUser to false


  // Optional: Only keep these if used
  const [aspectRatio, setAspectRatio] = useState("16:9");
  const [localVideoPath, setLocalVideoPath] = useState(null);
  const [validationError, setValidationError] = useState("");
  const [videoResolution, setVideoResolution] = useState(null);

  const [isProcessingVideo, setIsProcessingVideo] = useState(false); // Consider merging with 'processing'
  const navigate = useNavigate();

    

    
    const saveOriginalVideoToDB = async (videoTitle, s3Url, videoURL, localVideoPath, thumbnailUrl) => {
        if (!user || !user.uid) {
            console.log("❌ User not logged in. Cannot save data.");
            return;
        }
    
        // Ensure videoTitle is a valid Firestore document ID
        const formattedVideoTitle = videoTitle.replace(/\s+/g, " ");
    
        try {
            // 🔹 Reference to user's video document inside "videos" collection
            const videoRef = doc(db, "users", user.uid, "videos", videoTitle);
    
            // 🔹 Reference to "fetchedVideos" subcollection inside that document
            const fetchRef = doc(db, "users", user.uid, "videos", videoTitle, "fetchedVideos", "metadata");
    
            // 🔹 Save main details in "videos" collection (as a document)
            await setDoc(videoRef, {
                videoURL,
                title: formattedVideoTitle,
                originalS3Url: s3Url,
                localVideoPath,  // ✅ Save local path as a field
                thumbnailUrl,   // ✅ Added thumbnail URL
                timestamp: serverTimestamp(),  // Consistent Firestore timestamp
            }, { merge: true });
    
            console.log(`✅ Video details saved inside "videos" collection under document: ${videoTitle}`);
    
            // 🔹 Save details inside "fetchedVideos" subcollection
            await setDoc(fetchRef, {
                videoURL,
                title: videoTitle,
                originalS3Url: s3Url,
                localVideoPath,
                thumbnailUrl,  // ✅ Added thumbnail URL
                timestamp: serverTimestamp(),
            }, { merge: true });
    
            console.log("✅ Video details also saved inside 'fetchedVideos' subcollection.");
        } catch (error) {
            console.error("🔥 Error saving original video to Firestore:", error);
        }
    };
    
    
    
    
    
    
    
    
    const updateProcessingInDB = async (
        userId,
        videoTitle,
        formType,
        selectedFeatures,
        processedURL = null,
        seoData = null,
        response = null // 🟢 Add response parameter
    ) => {
        try {
            if (!userId || !videoTitle) {
                throw new Error("Invalid userId or videoTitle provided.");
            }
    
            console.log(`📌 Updating Firestore: users/${userId}/videos/${videoTitle}/generate/${formType}`);
    
            const videoRef = doc(db, "users", userId, "videos", videoTitle);
            await setDoc(videoRef, { createdAt: serverTimestamp() }, { merge: true });
    
            const generateVidRef = doc(db, "users", userId, "videos", videoTitle, "generate", formType);
    
            let updateData = {
                selectedFeatures: selectedFeatures || [],
                status: response?.status === 200 ? "Success" : "Processing", // ✅ Use response safely
                timestamp: serverTimestamp(),
            };
    
            if (processedURL) {
                updateData.processedURL = processedURL;
            }
    
            if (seoData && formType === "LongForm") {
                updateData.seo = seoData;
            }
    
            console.log("🚀 Data being saved:", updateData);
    
            await setDoc(generateVidRef, updateData, { merge: true });
    
            console.log(`✅ Updated successfully inside 'videos/${videoTitle}/generate/${formType}'`);
        } catch (error) {
            console.error("🔥 Firestore update error:", error.message);
        }
    };
    
    
    const handleFetch = async () => {
      setLoading(true);
      setError(null);
      setVideoData(null);
      setVideoResolution(null);
      setIsProcessingVideo(true);
    
      // Validate empty input
      if (!videoURL.trim()) {
        setError("❌ Please enter a valid YouTube URL.");
        setLoading(false);
        setIsProcessingVideo(false);
        return;
      }
    
      // YouTube URL validation
      const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/(watch\?v=|embed\/|v\/|shorts\/|live\/)[a-zA-Z0-9-_]+(&[a-zA-Z0-9=&]*)?$/;
      if (!youtubeRegex.test(videoURL)) {
        setError("❌ Invalid YouTube URL format. Please check and try again.");
        setLoading(false);
        setIsProcessingVideo(false);
        return;
      }
    
      try {
        // 1. Metadata Fetch Errors
        let data;
        try {
          data = await fetchVideoMetadata(videoURL);
          if (!data || !data.title || !data.thumbnail) {
            throw new Error("Invalid metadata response from server");
          }
        } catch (metadataError) {
          console.error("Metadata Error:", metadataError);
          let errorMessage = "❌ Failed to fetch video metadata. ";
          
          if (metadataError.response) {
            // Handle HTTP errors
            if (metadataError.response.status === 404) {
              errorMessage += "Video not found (404).";
            } else if (metadataError.response.status === 403) {
              errorMessage += "Video might be private or age-restricted (403).";
            } else {
              errorMessage += `Server responded with ${metadataError.response.status}.`;
            }
          } else if (metadataError.message.includes("Invalid metadata")) {
            errorMessage += "The video might not be accessible.";
          } else {
            errorMessage += "Please check your network connection.";
          }
    
          setError(errorMessage);
          setLoading(false);
          setIsProcessingVideo(false);
          return;
        }
    
        // 2. Video Download & Upload Errors
        let downloadResponse;
        try {
          downloadResponse = await downloadAndUploadVideo(videoURL);
          
          if (!downloadResponse?.url || !downloadResponse?.local_path) {
            throw new Error("Invalid download response");
          }
        } catch (downloadError) {
          console.error("Download/Upload Error:", downloadError);
          let errorMessage = "❌ Failed to process video. ";
          
          if (downloadError.response) {
            // Handle storage service errors
            if (downloadError.response.status === 413) {
              errorMessage += "Video file is too large.";
            } else if (downloadError.response.status === 502) {
              errorMessage += "Storage service unavailable.";
            } else {
              errorMessage += `Storage error (${downloadError.response.status}).`;
            }
          } else if (downloadError.message.includes("network")) {
            errorMessage += "Network connection failed during download.";
          } else if (downloadError.message.includes("storage quota")) {
            errorMessage += "Storage quota exceeded.";
          } else {
            errorMessage += "Please try a different video.";
          }
    
          setError(errorMessage);
          setLoading(false);
          setIsProcessingVideo(false);
          return;
        }
    
        const { url: s3Url, local_path: localPath } = downloadResponse;
    
        // 3. Database Save Errors
        try {
          if (!user?.uid) {
            throw new Error("User not authenticated");
          }
    
          await saveOriginalVideoToDB(
            data.title,
            s3Url,
            videoURL,
            localPath,
            data.thumbnail
          );
        } catch (dbError) {
          console.error("Database Error:", dbError);
          let errorMessage = "❌ Failed to save video details. ";
          
          if (dbError.message.includes("not authenticated")) {
            errorMessage += "Please log in to save videos.";
          } else if (dbError.code === "permission-denied") {
            errorMessage += "Database write permission denied.";
          } else if (dbError.code === "unavailable") {
            errorMessage += "Database service unavailable.";
          } else {
            errorMessage += "Please try again later.";
          }
    
          setError(errorMessage);
          setLoading(false);
          setIsProcessingVideo(false);
          return;
        }
    
        setLocalVideoPath(localPath);
    
        // 4. Resolution Check (Optional - shouldn't block flow)
        try {
          const resolutionResponse = await axios.post(
            "http://127.0.0.1:8000/api/check-resolution/",
            { video_path: localPath },
            { 
              headers: { "Content-Type": "application/json" },
              timeout: 2000000 // 10 second timeout
            }
          );
          
          if (resolutionResponse.data?.resolution) {
            setVideoResolution(resolutionResponse.data.resolution);
          }
        } catch (resError) {
          console.warn("Resolution Check Warning:", resError);
          // Non-critical failure - just log
        }
    
        // Success case
        setShowSuccessModal(true);
        setVideoData(data);
    
      } catch (unexpectedError) {
        console.error("Unexpected Error:", unexpectedError);
        setError("❌ An unexpected error occurred. Please try again.");
      } finally {
        setLoading(false);
        setIsProcessingVideo(false);
      }
    };
    
    const handleOptimizationTypeChange = (type) => {
        setOptimizationType(type);
        setAspectRatio(type === "Long Form" ? "16:9" : "9:16");
    };

    const handleFeatureToggle = (feature) => {
        if (feature === "Video Quality" && videoResolution && videoResolution.height > 480) {
            alert("Video quality optimization is only available for videos with resolution of 480p or lower. Your video has a higher resolution.");
            return;
        }

        setSelectedFeatures((prevFeatures) =>
            prevFeatures.includes(feature)
                ? prevFeatures.filter((f) => f !== feature)
                : [...prevFeatures, feature]
        );
    };
    

    const handleGenerateClick = async () => {
      if (!videoData) {
          alert("❌ Please fetch a video first before generating.");
          return;
      }
  
      if (!optimizationType) {
          alert("❌ Please select an optimization type (Long Form or Short Form).");
          return;
      }
  
      if (optimizationType === "Long Form" && selectedFeatures.length === 0) {
          alert("❌ Please select at least one feature for Long Form optimization.");
          return;
      }
  
      if (optimizationType === "Short Form" && (!clipLength || !clipCount)) {
          alert("❌ Please select clip length and number of clips for Short Form optimization.");
          return;
      }
  
      if (!user || !user.uid) {
          console.error("❌ User is not authenticated.");
          alert("❌ Please login before optimizing videos.");
          return;
      }
  
      const userId = user.uid;
      setProcessing(true);
      
      // Create error container element to display on UI if needed
      const showErrorMessage = (message) => {
          // You can implement a UI error display here or use existing error display component
          console.error("❌ Error:", message);
          alert(`❌ ${message}`);
      };
  
      try {
          const csrfToken = document.cookie
          .split("; ")
          .find((row) => row.startsWith("csrftoken"))?.split("=")[1] || "";
          
          if (!csrfToken) {
              console.warn("⚠️ CSRF token not found. This might cause API request issues.");
          }
          let sanitizedTitle = videoData.title.replace(/\s+/g, " ");
  
          const videoId = uuidv4();
          const payload = {
              videoURL,
              optimizationType: optimizationType === "Long Form" ? "LongForm" : "ShortForm",
              aspectRatio,
              selectedFeatures,
              localVideoPath,
              userId,
              videoId,
              userEmail: user?.email
          };
  
          let response;
          let processedURL = null;
  
          // ✅ Long Form Optimization
          if (optimizationType === "Long Form") {
              console.log("📌 Running Long Form Optimization...");
  
              try {
                  response = await axios.post("http://127.0.0.1:8000/api/seo/", payload, {
                      headers: { "Content-Type": "application/json" },
                  });
                  
                  console.log("✅ Response Data:", response.data);
                  
                  if (!response.data || !response.data.results) {
                      throw new Error("Invalid response format from the server");
                  }
                  
                  processedURL = response.data.results?.s3_upload?.url || null;
                  const clips = response.data.results?.clips || []; // Extract clips if available
                  const thumbnail = response.data.results?.thumbnail || null; // Extract thumbnail if available
  
                  // ✅ Construct saveData for Firestore
                  let saveData = {
                      userId,  // Ensure user ID is saved
                      videoId, // Ensure video ID is saved
                      selectedFeatures,
                      status: response?.status === 200 ? "Success" : "Processing",
                      timestamp: serverTimestamp(),
                  };
  
                  // ✅ Check if SEO is selected and store data accordingly
                  if (selectedFeatures.includes("SEO") && selectedFeatures.length === 1) {
                      // If ONLY SEO is selected, store in `seo` field
                      saveData.seo = response.data.results?.seo || {};
                  } else if (selectedFeatures.includes("SEO")) {
                      // If SEO + Other Features are selected, store in BOTH `seo` & `optimized_vid`
                      saveData.seo = response.data.results?.seo || {};
                      saveData.OptimizedVideo = {
                          originalVideoURL: videoURL,
                          processedVideoURL: processedURL,
                          s3FinalURL: processedURL,
                          s3Key: response.data.results?.s3_upload?.key || null,
                          localPath: localVideoPath || null,
                          enhancementType: response.data.results?.enhancementType || "Unknown",
                          status: response.data.results?.s3_upload?.status || "Processing",
                          message: response.data.message || "",
                      };
                  } 
  
                  try {
                      // ✅ Save Data to Firestore
                      await setDoc(
                          doc(db, `users/${userId}/videos/${sanitizedTitle}/generate/LongForm`),
                          saveData,
                          { merge: true }
                      );
                      console.log(`✅ Data saved under videoTitle: ${sanitizedTitle}`);
                  } catch (firestoreError) {
                      console.error("❌ Firestore save error:", firestoreError);
                      // Continue with navigation even if Firestore fails
                      // Just log the error but don't throw, so the user can still see results
                  }
  
                  // ✅ Redirect User Based on Features
                  if (selectedFeatures.includes("SEO")) {
                      const displayMedia = selectedFeatures.length === 1 ? thumbnail : (clips.length > 0 ? clips[0] : null);
  
                      navigate("/Seo", {
                          state: {
                              results: response.data.results,
                              videoURL,
                              localVideoPath,
                              selectedFeatures,
                              videoTitle: videoData.title,
                              displayMedia, // Thumbnail if only SEO, first clip if SEO + other features
                          },
                      });
                  } else {
                      navigate("/optimizevideo", {
                          state: {
                              videoURL,
                              results: response.data.results,
                              localVideoPath,
                              selectedFeatures,
                              userId,
                              videoTitle: videoData.title,
                          },
                      });
                  }
              } catch (longFormError) {
                  console.error("❌ Long Form API Error:", longFormError);
                  
                  if (longFormError.response) {
                      // The request was made and the server responded with a status code
                      // that falls out of the range of 2xx
                      if (longFormError.response.status === 400) {
                          showErrorMessage(`Bad request: ${longFormError.response.data.error || "Invalid input parameters"}`);
                      } else if (longFormError.response.status === 401 || longFormError.response.status === 403) {
                          showErrorMessage("Authentication error. Please log in again.");
                      } else if (longFormError.response.status === 404) {
                          showErrorMessage("API endpoint not found. Please contact support.");
                      } else if (longFormError.response.status === 500) {
                          showErrorMessage("Server error processing your video. Please try again later.");
                      } else {
                          showErrorMessage(`API error: ${longFormError.response.data.error || longFormError.message}`);
                      }
                  } else if (longFormError.request) {
                      // The request was made but no response was received
                      showErrorMessage("No response from server. Please check your internet connection.");
                  } else if (longFormError.message.includes("timeout")) {
                      showErrorMessage("Request timed out. Your video might be too large or our servers are busy.");
                  } else {
                      // Something happened in setting up the request that triggered an Error
                      showErrorMessage(`Error setting up request: ${longFormError.message}`);
                  }
                  throw longFormError; // Re-throw to prevent further execution
              }
          }
          // ✅ **Short Form Optimization**
          else if (optimizationType === "Short Form") {
              console.log("🎬 Running Short Form Optimization...");
  
              try {
                  response = await axios.post(
                      "http://127.0.0.1:8000/api/process_short_form_video/",
                      {
                          ...payload,
                          clipLength: Number(clipLength),
                          clipCount: Number(clipCount),
                      },
                      {
                          headers: {
                              "X-CSRFToken": csrfToken,
                              "Content-Type": "application/json",
                          },
                          
                      }
                  );
  
                  console.log("✅ Short Form Response:", response.data);
                  
                  if (!response.data || !response.data.clips) {
                      throw new Error("Invalid response format from the server");
                  }
                  
                  try {
                      await setDoc(
                          doc(db, `users/${userId}/videos/${sanitizedTitle}/generate/ShortForm`),
                          {
                              clipLength,
                              clipCount,
                              clips: response.data.clips || [],
                              status: response?.status === 200 ? "Success" : "Processing",
                              timestamp: serverTimestamp(),
                              videoTitle: videoData.title,
                              videoId,
                          },
                          { merge: true }
                      );
                      console.log(`✅ Short Form saved under videoTitle: ${sanitizedTitle}`);
                  } catch (firestoreError) {
                      console.error("❌ Firestore save error:", firestoreError);
                      // Continue with navigation even if Firestore fails
                  }
                  
                  navigate("/clippreview", {
                      state: {
                          clipPaths: response.data.clips,
                          videoURL,
                          videoTitle: videoData.title,
                      },
                  });
              } catch (shortFormError) {
                  console.error("❌ Short Form API Error:", shortFormError);
                  
                  if (shortFormError.response) {
                      if (shortFormError.response.status === 400) {
                          showErrorMessage(`Invalid parameters: ${shortFormError.response.data.error || "Please check your inputs"}`);
                      } else if (shortFormError.response.status === 401 || shortFormError.response.status === 403) {
                          showErrorMessage("Authentication error. Please log in again.");
                      } else if (shortFormError.response.status === 404) {
                          showErrorMessage("Short form processing endpoint not found.");
                      } else if (shortFormError.response.status === 500) {
                          showErrorMessage("Server error processing your short form clips. Please try again later.");
                      } else {
                          showErrorMessage(`API error: ${shortFormError.response.data.error || shortFormError.message}`);
                      }
                  } else if (shortFormError.request) {
                      showErrorMessage("No response from server. Please check your internet connection.");
                  } else if (shortFormError.message.includes("timeout")) {
                      showErrorMessage("Request timed out. Your video might be too large or our servers are busy.");
                  } else {
                      showErrorMessage(`Error setting up request: ${shortFormError.message}`);
                  }
                  throw shortFormError; // Re-throw to prevent further execution
              }
          }
      } catch (err) {
          console.error("❌ Error processing video:", err);
          
          // If the error wasn't already handled in the specific sections
          if (!err.handled) {
              // Check for network connectivity issues
              if (!navigator.onLine) {
                  alert("❌ You are offline. Please check your internet connection and try again.");
              } 
              // Handle Firebase/Firestore specific errors
              else if (err.code && err.code.startsWith('firestore/')) {
                  alert(`❌ Database error: ${err.message}`);
              }
              // Default error message if not caught by specific handlers
              else {
                  alert(err.response?.data?.error || err.message || "❌ An error occurred. Please try again.");
              }
          }
      } finally {
          setProcessing(false);
      }
  };
    const featureIcons = {
        "Noise Reduction": (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#55aaff" strokeWidth="2">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"></path>
          </svg>
        ),
        "Video Quality": (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#55ff99" strokeWidth="2">
            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"></path>
          </svg>
        ),
        "SEO": (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#ffdd55" strokeWidth="2">
            <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"></path>
          </svg>
        )
      };
      const SuccessModal = () => {
        if (!showSuccessModal) return null;
        
        return (
          <div className="success-modal-overlay">
            <div className="success-modal">
              <div className="success-icon">✅</div>
              <h3>Video Processing Complete!</h3>
              <p>Your video has been successfully fetched and saved to the cloud.</p>
              <button 
                className="modal-close-btn"
                onClick={() => setShowSuccessModal(false)}
              >
                Continue
              </button>
            </div>
          </div>
        );
      };
    

      return (
        <>
          {/* Navbar - Only visible when explicitly navigating to clipper */}
          {window.location.pathname !== "/home" && (
            <header className="header">
              <div className="header__logo" onClick={() => navigate("/home")}>
                Channel<span className="header__logo-highlight">IQ</span>
              </div>
      
              {loadingUser ? (
                <p className="loading-text">Loading user...</p>
              ) : user ? (
                <div className="user">
                  {user.picture && (
                    <img src={user.picture} alt="User" className="user__avatar" />
                  )}
                  <span className="user__name">{user.name}</span>
                  <button className="user__logout-btn" onClick={logout}>
                    Logout
                  </button>
                </div>
              ) : (
                <button className="user__login-btn" onClick={() => navigate("/login")}>
                  Login
                </button>
              )}
            </header>
          )}
      
          <div className="clipper-wrapper">
            <div className="clipper-container">
              {/* Title */}
              <div className="app-title">
                <h1>
                  <span className="channel">Channel</span>
                  <span className="iq">IQ</span>
                </h1>
              </div>
      
              {/* URL Input */}
              <div className="url-input-container">
                <input
                  type="text"
                  placeholder="https://www.youtube.com/watch?v=jNQXAC9IVRw"
                  value={videoURL}
                  onChange={(e) => setVideoURL(e.target.value)}
                  className="input"
                  disabled={loading || isProcessingVideo}
                />
                <button
                  onClick={handleFetch}
                  disabled={loading || isProcessingVideo || !videoURL}
                  className="fetch-btn"
                >
                  {loading ? (
                    <span className="loading-spinner">
                      <span className="spinner-dot"></span>
                      <span className="spinner-dot"></span>
                      <span className="spinner-dot"></span>
                    </span>
                  ) : (
                    "Fetch"
                  )}
                </button>
              </div>
      
              {/* Processing Overlay */}
              {isProcessingVideo && !videoData && (
                <div className="processing-overlay">
                  <div className="processing-content">
                    <div className="processing-spinner">
                      <div className="spinner-ring"></div>
                    </div>
                    <h3>Processing Your Video</h3>
                    <p>Please wait while we fetch and save your video to the cloud...</p>
                  </div>
                </div>
              )}
      
              {/* Main Content */}
              {!isProcessingVideo && (
                <div className="main-content-container">
                  {/* Video and Settings Wrapper */}
                  {videoData ? (
                    <div className="video-settings-wrapper">
                      <div className="video-settings-content">
                        {/* Video Preview Container */}
                        <div className="video-preview-container visible">
                          <div className="video-data-container">
                            <div className="video-section">
                              <h3 className="section-heading">Thumbnail:</h3>
                              <div className="video-thumbnail-container">
                                <img
                                  src={videoData.thumbnail}
                                  alt="Video Thumbnail"
                                  className="video-thumbnail"
                                />
                              </div>
                            </div>
                            <div className="video-section">
                              <h3 className="section-heading">Title:</h3>
                              <div className="video-title-container">
                                <h4 className="video-title" title={videoData.title}>
                                  {videoData.title}
                                </h4>
                              </div>
                            </div>
                          </div>
                        </div>
      
                        {/* Settings Container */}
                        <div className="settings-container">
                          <div className="optimization-type">
                            <h3>Choose Optimization Type:</h3>
                            <div className="optimization-buttons">
                              {["Long Form", "Short Form"].map((type) => (
                                <button
                                  key={type}
                                  className={`btn ${
                                    optimizationType === type ? "btn--primary" : "btn--outline"
                                  }`}
                                  onClick={() => handleOptimizationTypeChange(type)}
                                >
                                  {type}
                                </button>
                              ))}
                            </div>
                          </div>
      
                          {optimizationType === "Long Form" && (
                            <div className="features">
                              <h3>Select Features:</h3>
                              <div className="feature-buttons">
                                {["Noise Reduction", "Video Quality", "SEO"].map((feature) => (
                                  <button
                                    key={feature}
                                    className={`feature-btn ${
                                      selectedFeatures.includes(feature) ? "active" : ""
                                    }`}
                                    onClick={() => handleFeatureToggle(feature)}
                                  >
                                    <div className="feature-icon">{featureIcons[feature]}</div>
                                    <span>{feature}</span>
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
      
                          {optimizationType === "Short Form" && (
                            <div className="short-form-options">
                              <div className="dropdown-container form-control">
                                <label htmlFor="clipLength">Clip Length:</label>
                                <select
                                  id="clipLength"
                                  value={clipLength}
                                  onChange={(e) => setClipLength(e.target.value)}
                                  className="input"
                                >
                                  <option value="30">30 seconds</option>
                                  <option value="60">60 seconds</option>
                                  <option value="90">90 seconds</option>\
                                  <option value="Auto">Auto</option>
                                </select>
                              </div>
                              <div className="clip-count-container form-control">
                    <label htmlFor="clipCount">Number of Clips (1-3):</label>
                    <select
                      id="clipCount"
                      value={clipCount}
                      onChange={(e) => setClipCount(parseInt(e.target.value))}
                      className="select"
                    >
                      <option value={1}>1</option>
                      <option value={2}>2</option>
                      <option value={3}>3</option>
                    </select>
                  </div>

                            </div>
                          )}
                        </div>
                      </div>
      
                      {/* Action Buttons Container */}
                      <div className="action-buttons-container">
                        <div className="generate-btn">
                          <button
                            onClick={handleGenerateClick}
                            disabled={processing || !videoData}
                            className="btn btn--primary"
                          >
                            {processing ? "Processing..." : "Generate"}
                          </button>
                        </div>
                        <div className="show-dashboard-btn">
                          <button
                            className="btn--outline"
                            onClick={() => setShowDashboard(!showDashboard)}
                          >
                            {showDashboard ? "Hide Videos" : "Show Videos"}
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Placeholder when no video is loaded */
                    <div className="main-placeholder-wrapper">
                      <div className="no-video-placeholder">
                        <div className="placeholder-content">
                          <span className="placeholder-icon">🎬</span>
                          <p>Enter a YouTube URL and click "Fetch Vid" to get started</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
      
              {/* Dashboard Section */}
              {showDashboard && (
                <div className="video-dashboard-container">
                  <VideoDashboard />
                </div>
              )}
      
              {/* Success Modal */}
              <SuccessModal />
            </div>
          </div>
        </>
      );
    }
export default Clipper;