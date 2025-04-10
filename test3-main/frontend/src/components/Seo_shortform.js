import React, { useState, useContext, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { UserContext } from "./UserContext"; // Import User Context
import { db } from "../Firebase"; // Import Firestore Database
import { doc, setDoc, collection, serverTimestamp } from "firebase/firestore";
import "./Seo_shortform.css";

function Seo_shortform({ videoThumbnail }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Get user session
  const { message, results, selectedFeatures, selectedClip } = location.state || {};
  const [seoMessage, setSeoMessage] = useState(message || "No SEO data received.");
  const [uploading, setUploading] = useState(false);
  const [authorizing, setAuthorizing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [hasYoutubeAuth, setHasYoutubeAuth] = useState(false);

  // Extract SEO data for easier access
  const seoData = results?.seo || {};
  const keywords = seoData.keywords?.join(", ") || "No keywords available.";
  const description = seoData.description || "No description available.";
  const title = seoData.title || "No title available.";
  const tags = seoData.hashtags?.join(", ") || "No tags available.";

  // Check for videoTitle from previous page
  const videoTitle = location.state?.videoTitle || null;

  // If no title found from previous page, show an error
  useEffect(() => {
    if (!videoTitle) {
      alert("⚠️ No title found from previous page!");
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

  // ✅ Save SEO Short Form Details
  const saveSEOToDB = async (user, videoTitle, title, description, tags, keywords) => {
    if (!user) return console.error("❌ User not logged in.");
    const extractedUserId = user?.uid;
    if (!extractedUserId) return console.error("❌ No userId found.");
    if (!videoTitle?.trim()) return console.error("❌ Error: videoTitle is empty.");

    try {
      const sanitizedTitle = videoTitle.replace(/\s+/g, " ");
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

  // ✅ Save Video Details


  // ✅ Automatically Save Data
  useEffect(() => {
    if (videoTitle && videoTitle !== "No title available." && user) {
      const sanitizedTitle = videoTitle.trim();
      saveSEOToDB(user, sanitizedTitle, title, description, tags, keywords);
    }
  }, [videoTitle, title, description, tags, keywords, selectedClip, selectedFeatures, user]);

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
    if (selectedFeatures?.length === 1 && selectedFeatures?.includes("SEO")) {
      return selectedClip.url || selectedClip;
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
    return selectedClip?.url || selectedClip;
  };

  const handleCompare = () => {
    // Extract the original clip information for comparison
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
        seoData: null
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
                <p>{title}</p>
              </div>
              <div className="seo-box">
                <h2>Description</h2>
                <p>{description}</p>
              </div>
              <div className="seo-box">
                <h2>Keywords</h2>
                <p>{keywords}</p>
              </div>
              <div className="seo-box">
                <h2>Tags</h2>
                <p>{tags}</p>
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
                  className={`youtube-upload-btn ${uploading ? 'uploading' : ''}`}
                  onClick={handleUploadToYouTube}
                  disabled={uploading || !user}
                >
                  {uploading ? "Uploading..." : "Upload to YouTube"}
                </button>
              )}
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
                <p>
                  <strong>Note:</strong> To upload videos to YouTube, you need to connect 
                  Channel-IQ to your YouTube account.
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