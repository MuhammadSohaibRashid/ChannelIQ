import React, { useState, useContext, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { UserContext } from "./UserContext"; // Import User Context
import { db } from "../Firebase"; // Import Firestore Database
import { doc, setDoc, serverTimestamp } from "firebase/firestore";
import "./Seo_shortform.css";

function Seo_shortform({ videoThumbnail }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Get user session
  const { message, results, selectedFeatures, selectedClip, videoTitle: initialVideoTitle } = location.state || {};
  const [seoMessage, setSeoMessage] = useState(message || "No SEO data received.");
  const [uploading, setUploading] = useState(false);
  const [authorizing, setAuthorizing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [hasYoutubeAuth, setHasYoutubeAuth] = useState(false);
  const [videoTitle, setVideoTitle] = useState(initialVideoTitle || "");
  
  // Check if only SEO is selected
  const isSeoOnly = selectedFeatures?.length === 1 && selectedFeatures?.includes("SEO");

  // Extract SEO data for easier access
  const seoData = results?.seo || {};
  const keywords = seoData.keywords?.join(", ") || "No keywords available.";
  const description = seoData.description || "No description available.";
  const title = seoData.title || "No title available.";
  const tags = seoData.hashtags?.join(", ") || "No tags available.";

  useEffect(() => {
      if (location.state) {
        console.log("Received data from previous page:", location.state);
        if (location.state.videoTitle) {
          setVideoTitle(location.state.videoTitle);
        }
      }
    }, [location.state]);
      // If no title found from previous page, show an error
  useEffect(() => {
      if (!videoTitle) {
        console.warn("⚠️ No title found from previous page!");
      }
    }, [videoTitle]);

  console.log("🚀 Video Title from Previous Page:", videoTitle || "No title found");

  // Check for YouTube authorization on component mount
  useEffect(() => {
    const token = localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
    setAuthToken(token);
    if (results?.final_processed?.s3_url) {
      console.log(results.final_processed.s3_url);
    }
    // Check if user has YouTube authorization
    if (token && user) {
      checkYoutubeAuth(token);
    }
  }, [user]);

  // ✅ Save SEO Short Form Details to a seo field in the ShortForm document
  const saveSEOToDB = async (user, videoTitle, title, description, tags, keywords) => {
    if (!user) return console.error("❌ User not logged in.");
    const extractedUserId = user?.uid;
    if (!extractedUserId) return console.error("❌ No userId found.");
    if (!videoTitle?.trim()) return console.error("❌ Error: videoTitle is empty.");

    try {
      const sanitizedTitle = videoTitle.replace(/[^\w\s-]/gi, "").trim();
      const clipDocRef = doc(db, `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`);
      const seoData = {
        title: title || "Untitled",
        description: description || "No description available.",
        tags: tags || [],
        keywords: keywords || [],
        timestamp: serverTimestamp(),
      };
      await setDoc(clipDocRef, { seo: seoData }, { merge: true });
      console.log("✅ SEO Short Form details saved.");
    } catch (error) {
      console.error("🔥 Error saving SEO data:", error);
    }
  };

// ✅ Save Video Details to a videodetails field in the ShortForm document
const saveOptimizationDetails = async ({
    processedVideoURL,
    originalVideoURL,
    enhancementType,
    selectedFeatures,
    videoTitle,
    audio_processing,
    email_notification,
    final_processed
  }) => {
    console.log("🔄 saveOptimizationDetails called from SEO component");
  
    if (!user) {
      console.log("❌ User not logged in. Cannot save video details.");
      return;
    }
  
    // ✅ Log incoming data
    console.log("🛠 Incoming Data from SEO component:");
    console.log("🎵 audio_processing:", audio_processing);
    console.log("📧 email_notification:", email_notification);
    console.log("🎞 final_processed:", final_processed);
    console.log("🏷 videoTitle:", videoTitle);
    console.log("🔗 status:", processedVideoURL);
  
    try {
      // Sanitize or generate title
      let sanitizedTitle = videoTitle
        ? videoTitle.replace(/[^\w\s-]/gi, "").trim()
        : `video_${Date.now()}`;
      let originalTitle = videoTitle || "Unknown Video";
  
      if (!sanitizedTitle) {
        sanitizedTitle = `video_${Date.now()}`;
        originalTitle = "Unknown Video";
      }
  
      const clipDocRef = doc(
        db,
        `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`
      );
  
      // ✅ Build OptimizedVid object
      const optimizedVidData = {};
      if (audio_processing && typeof audio_processing === "object") {
        optimizedVidData.audio_processing = audio_processing;
      }
      if (email_notification && typeof email_notification === "object") {
        optimizedVidData.email_notification = email_notification;
      }
      if (final_processed && typeof final_processed === "object") {
        optimizedVidData.final_processed = final_processed;
      }
      
      // Add additional metadata

      optimizedVidData.enhancementType = enhancementType;
      optimizedVidData.selectedFeatures = selectedFeatures;
  
      console.log("📦 Final OptimizedVid object from SEO:", optimizedVidData);
  
      const dataToSave = {
        OptimizedVid: optimizedVidData,
        videoTitle: originalTitle,
        timestamp: serverTimestamp(),
      };
  
      await setDoc(clipDocRef, dataToSave, { merge: true });
  
      console.log("✅ Optimized video details saved successfully from SEO component!");
    } catch (error) {
      console.error("🔥 Error saving optimized video details from SEO:", error);
    }
  };

  // ✅ Automatically Save Data
  useEffect(() => {
      if (videoTitle && videoTitle !== "No title available." && user) {
        const sanitizedTitle = videoTitle.trim();
    
        // Save SEO
        saveSEOToDB(user, sanitizedTitle, title, description, tags, keywords);
    
        // Save OptimizedVid if we have results data
        if (
          results?.audio_processing ||
          results?.email_notification ||
          results?.final_processed ||
          selectedClip
        ) {
          // Determine enhancement types based on selected features
          let enhancementLabel = "";
          
          if (selectedFeatures?.includes("Video Quality")) {
            enhancementLabel = "Video Enhanced";
          }
          
          if (selectedFeatures?.includes("Noise Reduction")) {
            enhancementLabel = enhancementLabel ? "Audio & Video Enhanced" : "Audio Enhanced";
          }
          
          if (selectedFeatures?.includes("Captions")) {
            enhancementLabel = enhancementLabel ? `${enhancementLabel}, Captions Added` : "Captions Added";
          }
  
          if (selectedFeatures?.includes("SEO") && !enhancementLabel) {
            enhancementLabel = "SEO Optimized";
          }
  
          // Get best video URL
          const processedVideoURL = 
            results?.final_processed?.s3_url || 
            results?.audio_processing?.s3_url || 
            results?.video_upscaling?.s3_url || 
            results?.captions?.s3_url || 
            (typeof selectedClip === 'object' ? selectedClip.url : selectedClip);
  
          saveOptimizationDetails({
            processedVideoURL: processedVideoURL,
            enhancementType: enhancementLabel,
            selectedFeatures: selectedFeatures || [],
            videoTitle: sanitizedTitle,
            audio_processing: results?.audio_processing || null,
            email_notification: results?.email_notification || null,
            final_processed: results?.final_processed || null,
          });
        }
      }
    }, [
      videoTitle,
      title,
      description,
      tags,
      keywords,
      selectedClip,
      selectedFeatures,
      user,
      results, // include this so it triggers when results change
    ]);

  // Function to check if user has YouTube authorization
  const checkYoutubeAuth = async (token) => {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/youtube/check-auth/", {
        method: "GET",
        headers: {
          Authorization: `Token ${token}`,
        },
      });
      
      const data = await response.json();
      console.log("YouTube Auth Data:", data);
      setHasYoutubeAuth(data.has_youtube_auth || false);
    } catch (error) {
      console.error("Error checking YouTube auth:", error);
      setHasYoutubeAuth(false);
    }
  };

  const getVideoUrl = () => {
    // If SEO is the only selected feature, return the selected clip URL directly
    if (isSeoOnly) {
      return typeof selectedClip === 'object' ? selectedClip.url : selectedClip;
    }

    // For processed files, use the S3 URL when available in results
    if (results?.final_processed?.s3_url) {
      return results.final_processed.s3_url;
    }

    // Fallback to processed file paths for local development/testing
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

    // Return selectedClip URL or fallback to the object itself
    return typeof selectedClip === 'object' ? selectedClip.url : selectedClip;
  };

  const handleCompare = () => {
    const originalClipData = typeof selectedClip === 'object' 
      ? { 
          url: selectedClip.url,
          key: selectedClip.key
        }
      : { 
          url: selectedClip,
          key: selectedClip.split("/").pop()
        };
  
    navigate("/comparison", {
      state: {
        results: results,
        selectedFeatures,
        videoURL: originalClipData.url,
        s3Key: originalClipData.key,
        localVideoPath: `\\media\\videos\\${originalClipData.key.split("/").pop()}`,
        processedS3Url: results?.final_processed?.s3_url || getVideoUrl(),
        // Only include seoData if SEO is not the only selected feature
        ...(isSeoOnly ? {} : { seoData: null })
      }
    });
  };

  const handleAuthorizeYouTube = async () => {
    if (!authToken) {
      setUploadStatus({
        success: false,
        message: "Authentication token not found. Please log in again."
      });
      return;
    }

    setAuthorizing(true);
    setUploadStatus(null);

    try {
      const authResponse = await fetch("http://127.0.0.1:8000/api/youtube/get-auth-url/", {
        method: "GET",
        headers: {
          Authorization: `Token ${authToken}`,
          "Content-Type": "application/json"
        }
      });
      
      if (!authResponse.ok) {
        throw new Error(`Failed to get auth URL: ${authResponse.status} ${authResponse.statusText}`);
      }
      
      const authData = await authResponse.json();
      
      if (authData.auth_url) {
        // Open the authorization URL in a new window
        const authWindow = window.open(authData.auth_url, "YouTubeAuth", "width=600,height=700");
        
        // Poll to check if auth is complete
        const checkAuthInterval = setInterval(async () => {
          try {
            const checkResponse = await fetch("http://127.0.0.1:8000/api/youtube/check-auth/", {
              method: "GET",
              headers: {
                Authorization: `Token ${authToken}`,
              },
            });
            
            const checkData = await checkResponse.json();
            
            if (checkData.has_youtube_auth) {
              // Auth is complete, close polling and window
              clearInterval(checkAuthInterval);
              setHasYoutubeAuth(true);
              setUploadStatus({
                success: true,
                message: "YouTube account successfully connected!"
              });
              
              if (authWindow && !authWindow.closed) {
                authWindow.close();
              }
            }
          } catch (error) {
            console.error("Error checking auth status:", error);
          }
        }, 2000); // Check every 2 seconds
        
        // Cleanup interval after 5 minutes (maximum waiting time)
        setTimeout(() => {
          clearInterval(checkAuthInterval);
          setUploadStatus({
            success: false,
            message: "Authorization timed out. Please try again."
          });
        }, 300000); // 5 minutes
      } else {
        throw new Error("No authorization URL received from server");
      }
    } catch (error) {
      console.error("Authorization error:", error);
      setUploadStatus({
        success: false,
        message: `Failed to authorize: ${error.message}`
      });
    } finally {
      setAuthorizing(false);
    }
  };

  const handleUploadToYouTube = async () => {
    if (!user) {
      setUploadStatus({
        success: false,
        message: "You must be logged in to upload to YouTube"
      });
      return;
    }
  
    if (!authToken) {
      setUploadStatus({
        success: false,
        message: "Authentication token not found. Please log in again."
      });
      return;
    }
  
    setUploading(true);
    setUploadStatus(null);
  
    try {
      // Get the video URL
      const videoUrl = getVideoUrl();
      
      // Create form data for file upload
      const formData = new FormData();
      
      formData.append('video_url', videoUrl);
      formData.append('title', results?.seo?.title || "My Video");
      formData.append('description', results?.seo?.description || "");
      formData.append('tags', results?.seo?.hashtags?.join(",") || "");
      
      if (selectedClip?.key) {
        formData.append('s3_key', selectedClip.key);
      }
      
      console.log("Uploading with token:", authToken);
      
      // Make the API request to upload the video
      const uploadResponse = await fetch("http://127.0.0.1:8000/api/youtube/upload/", {
        method: "POST",
        headers: {
          Authorization: `Token ${authToken}`
        },
        body: formData,
      });
      
      const data = await uploadResponse.json();
      
      // Check if we need to re-authorize YouTube
      if (!uploadResponse.ok) {
        if (uploadResponse.status === 401 && data.needs_auth) {
          // YouTube auth needs renewal
          setHasYoutubeAuth(false);
          setUploadStatus({
            success: false,
            message: data.detail || "Your YouTube authorization has expired. Please reconnect your YouTube account.",
            needsAuth: true
          });
          return;
        }
        throw new Error(`Upload failed with status: ${uploadResponse.status} ${uploadResponse.statusText}`);
      }
      
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
        message: `An error occurred during upload: ${error.message}`
      });
    } finally {
      setUploading(false);
    }
  };

   // Handle copy functionality for SEO data
   const handleCopy = (text) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        alert("Copied to clipboard!");
      })
      .catch(err => {
        console.error('Failed to copy text: ', err);
      });
  };

  return (
    <div className="seo-app">
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


      <main className="main-content">
    
       {/* Replace your clip-section div with this updated version */}
<div className="clip-section">
  <div className="clip-container">
    <div className="clip-content-wrapper">
      <div className="media-preview">
        <video className="preview-video" controls>
          <source src={getVideoUrl()} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      </div>

      <div className="customize-clip">
        <div className="seo-container">
          <h3 className="seo-label">SEO Details</h3>
          <div className="seo-data">
            <div className="seo-box">
              <h2>Title</h2>
              <button className="copy-btn" onClick={() => handleCopy(title)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
              <p>{title}</p>
            </div>
            <div className="seo-box">
              <h2>Description</h2>
              <button className="copy-btn" onClick={() => handleCopy(description)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
              <p>{description}</p>
            </div>
            <div className="seo-box">
              <h2>Keywords</h2>
              <button className="copy-btn" onClick={() => handleCopy(keywords)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
              <p>{keywords}</p>
            </div>
            <div className="seo-box">
              <h2>Tags</h2>
              <button className="copy-btn" onClick={() => handleCopy(tags)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
              <p>{tags}</p>
            </div>
          </div>
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
        {user && !hasYoutubeAuth && !authorizing && (
          <div className="youtube-auth-note">
            {/* Your authorization note content */}
          </div>
        )}
      </div>
    </div>
    <div className="content-container-seo">
                            
      <div className="action-buttons">
        {/* Only show Compare Results button when SEO is not the only selected feature */}
        {!isSeoOnly && (
          <button className="comparison-btn" onClick={handleCompare}>
            Compare Results
          </button>
        )}
        
        {/* YouTube Auth/Upload Buttons */}
        {user && !hasYoutubeAuth ? (
          <button 
            className="youtube-auth-btn"
            onClick={handleAuthorizeYouTube}
            disabled={authorizing}
          >
            {authorizing ? "Authorizing..." : "Connect YouTube"}
          </button>
        ) : (
          <button 
            className={`youtube-upload-btn ${uploading ? 'uploading' : ''}` }
            onClick={handleUploadToYouTube}
            disabled={uploading || !user}
            style={{
              backgroundColor: '#8f3af5',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              marginTop: '20px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: '600',
              transition: 'all 0.3s ease',
              boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)'
            }}
          >
            {uploading ? "Uploading..." : "Upload to YouTube"}
          </button>
        )}
      </div>
    </div>
    {/* Action buttons moved here - at the bottom of clip-container */}
    <div className="action-buttons">
      {(selectedFeatures?.includes("Noise Reduction") ||
        selectedFeatures?.includes("Video Quality") ||
        selectedFeatures?.includes("Captions"))}
      
    </div>
  </div>
</div>
      </main>
    </div>
  );
}

export default Seo_shortform;