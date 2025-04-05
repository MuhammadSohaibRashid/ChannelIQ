import React, { useState, useEffect, useContext } from "react";
import "./Seo.css";
import { useLocation, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFileLines, faClosedCaptioning, faSearch, faImage } from "@fortawesome/free-solid-svg-icons";
import { fetchVideoMetadata } from "../axios-use/api";
import { UserContext } from "./UserContext"; // Import User Context
import { db } from "../Firebase";  // Import Firebase Firestore
import { addDoc, getDoc, doc, setDoc, collection, query, where, serverTimestamp } from "firebase/firestore";

function SEO({ videoThumbnail }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Access User Context

  const { videoTitle, message, results, videoURL, localVideoPath, selectedFeatures } = location.state || {};
  
  // ✅ Debugging Logs
  console.log("🔍 Debug: location.state =>", location.state);
  console.log(results);

  // ✅ Fix: Ensure `displayMedia` or `selectedClip` is received
  const displayMedia = location.state?.displayMedia || null; 
  const selectedClip = location.state?.selectedClip || null; 

  console.log("🔍 Debug: displayMedia (Thumbnail/Clip) =>", displayMedia);
  console.log("🔍 Debug: selectedClip (if available) =>", selectedClip);

  const [seoMessage, setSeoMessage] = useState(message || "No SEO data received.");
  const [displayVideo, setDisplayVideo] = useState(selectedClip || null);
  const [thumbnail, setThumbnail] = useState(displayMedia || videoThumbnail || "/default-thumbnail.png");
  const [uploading, setUploading] = useState(false);
  const [authorizing, setAuthorizing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [hasYoutubeAuth, setHasYoutubeAuth] = useState(false);

  const seoData = results?.seo || {};
  const keywords = seoData.keywords?.length ? seoData.keywords.join(", ") : "No keywords available.";
  const description = seoData.description || "No description available.";
  const title = seoData.title || "No title available.";
  const tags = seoData.tags?.length ? seoData.tags.join(", ") : "No tags available.";

  // ✅ Helper function to format text with line breaks
  const formatWithLineBreaks = (text) => {
    if (!text) return "";
    
    // Replace all newline characters with <br /> tags
    return text.split('\n').map((line, index) => (
      <React.Fragment key={index}>
        {line}
        {index < text.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };

  // ✅ Firebase function to save SEO data
  const saveSEOToDB = async (user, videoTitle, title, description, tags, keywords) => {
    if (!user) {
        console.error("❌ User not logged in. Cannot save SEO data.");
        return;
    }

    const extractedUserId = user?.uid;
    if (!extractedUserId) {
        console.error("❌ No userId found.");
        return;
    }

    // ✅ Step 1: Sanitize the video title
    let sanitizedTitle = videoTitle
        ? videoTitle.replace(/[^\w\s]/gi, "").trim()
        : `video_${Date.now()}`;

    if (!sanitizedTitle || sanitizedTitle.trim() === "") {
        console.error("❌ Error: Sanitized video title is empty.");
        return;
    }

    try {
        // ✅ Step 2: Firestore Path to store in 'LongForm'
        const longFormRef = doc(db, "users", extractedUserId, "videos", sanitizedTitle, "generate", "LongForm");

        // ✅ Step 3: Ensure `tags` and `keywords` are always arrays before joining
        const formattedTags = Array.isArray(tags) && tags.length > 0 ? tags.join(", ") : "No tags available.";
        const formattedKeywords = Array.isArray(keywords) && keywords.length > 0 ? keywords.join(", ") : "No keywords available.";

        // ✅ Step 4: Store all SEO details under a single "seo" field
        const seoData = {
            title: title || "Untitled",
            description: description || "No description available.",
            tags: formattedTags,
            keywords: formattedKeywords,
            timestamp: serverTimestamp(), // Firestore timestamp
        };

        console.log("📂 Firestore Path:", longFormRef.path);
        console.log("🔍 Debug: Saving SEO Data:", JSON.stringify(seoData, null, 2));

        // ✅ Step 5: Save SEO Data to Firestore under "seo" field
        await setDoc(longFormRef, { seo: seoData }, { merge: true });

        console.log("✅ SEO details successfully saved inside LongForm subcollection.");
    } catch (error) {
        console.error("🔥 Error saving SEO data:", error);
    }
  };

  // ✅ Automatically Save SEO Data when Component Loads
  useEffect(() => {
    if (user && videoTitle && title && description && (Array.isArray(seoData.tags) || tags)) {
      saveSEOToDB(user, videoTitle, title, description, seoData.tags || tags, seoData.keywords || keywords);
    }
  }, [user, videoTitle, title, description, tags, keywords, seoData.tags, seoData.keywords]);

  // Check for YouTube authorization on component mount
  useEffect(() => {
    const token = localStorage.getItem("authToken") || sessionStorage.getItem("authToken");
    setAuthToken(token);
    
    // Check if user has YouTube authorization
    if (token && user) {
      checkYoutubeAuth(token);
    }
  }, [user]);

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

  useEffect(() => {
    const fetchMedia = async () => {
      console.log("Results:", results);
      console.log("selectedFeatures:", selectedFeatures);
      try {
        // First check S3 uploaded versions (highest priority)
        if (results?.s3_upload?.url) {
          setDisplayVideo(results.s3_upload.url);
          console.log("Using S3 uploaded video:", results.s3_upload.url);
        }
        // Check for S3 links in specific processing results
        else if (results?.audio_processing?.s3_processed_file_path) {
          setDisplayVideo(results.audio_processing.s3_processed_file_path);
          console.log("Using S3 audio-enhanced video:", results.audio_processing.s3_processed_file_path);
        }
        else if (results?.video_upscaling?.s3_processed_file_path) {
          setDisplayVideo(results.video_upscaling.s3_processed_file_path);
          console.log("Using S3 upscaled video:", results.video_upscaling.s3_processed_file_path);
        }
        // Then check local processed files
        else if (results?.audio_processing?.processed_file_path) {
          const filename = results.audio_processing.processed_file_path.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/processed/${filename}`);
          console.log("Using local audio-enhanced video:", filename);
        } 
        else if (results?.video_upscaling?.processed_file_path) {
          const filename = results.video_upscaling.processed_file_path.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/processed/${filename}`);
          console.log("Using local upscaled video:", filename);
        }
        // Finally check original local video
        else if (localVideoPath) {
          const filename = localVideoPath.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/${filename}`);
          console.log("Using original local video:", filename);
        }
        // Last option: Fall back to YouTube thumbnail
        else {
          setDisplayVideo(null);
          if (videoURL) {
            try {
              const data = await fetchVideoMetadata(videoURL);
              if (data.thumbnail) {
                setThumbnail(data.thumbnail);
                console.log("Using YouTube thumbnail:", data.thumbnail);
              }
            } catch (error) {
              console.error("Error fetching video metadata:", error);
            }
          }
        }
      } catch (error) {
        console.error("Error setting up video display:", error);
        setDisplayVideo(null);
      }
    };

    fetchMedia();
  }, [results, videoURL, localVideoPath]);

  const getVideoUrl = () => {
    // First check S3 uploaded versions (highest priority)
    if (results?.s3_upload?.url) {
      return results.s3_upload.url;
    }
    // Check for S3 links in specific processing results
    else if (results?.audio_processing?.s3_processed_file_path) {
      return results.audio_processing.s3_processed_file_path;
    }
    else if (results?.video_upscaling?.s3_processed_file_path) {
      return results.video_upscaling.s3_processed_file_path;
    }
    // Then check local processed files
    else if (results?.audio_processing?.processed_file_path) {
      const filename = results.audio_processing.processed_file_path.split("\\").pop();
      return `http://127.0.0.1:8000/media/processed/${filename}`;
    } 
    else if (results?.video_upscaling?.processed_file_path) {
      const filename = results.video_upscaling.processed_file_path.split("\\").pop();
      return `http://127.0.0.1:8000/media/processed/${filename}`;
    }
    // Check original local video
    else if (localVideoPath) {
      const filename = localVideoPath.split("\\").pop();
      return `http://127.0.0.1:8000/media/${filename}`;
    }
    
    return videoURL;
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

  const handleUpdateSEO = async () => {
    if (!user) {
      setUploadStatus({
        success: false,
        message: "You must be logged in to update YouTube SEO"
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

    if (!hasYoutubeAuth) {
      setUploadStatus({
        success: false,
        message: "You need to connect your YouTube account first"
      });
      return;
    }

    // Check if we have a valid video URL
    if (!videoURL || !videoURL.includes("youtube.com")) {
      setUploadStatus({
        success: false,
        message: "This feature only works with YouTube videos"
      });
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      // Extract video ID from URL
      let videoId = "";
      if (videoURL.includes("v=")) {
        videoId = videoURL.split("v=")[1].split("&")[0];
      } else if (videoURL.includes("youtu.be/")) {
        videoId = videoURL.split("youtu.be/")[1].split("?")[0];
      }

      if (!videoId) {
        throw new Error("Could not extract video ID from URL");
      }

      // Create form data with updated SEO info
      const formData = new FormData();
      formData.append("video_id", videoId);
      formData.append("title", seoData.title || title);
      formData.append("description", seoData.description || description);
      formData.append("tags", seoData.tags?.join(",") || "");

      // Make API call to update video metadata
      const updateResponse = await fetch("http://127.0.0.1:8000/api/youtube/update-seo/", {
        method: "POST",
        headers: {
          Authorization: `Token ${authToken}`,
        },
        body: formData,
      });

      if (!updateResponse.ok) {
        throw new Error(`Update failed with status: ${updateResponse.status} ${updateResponse.statusText}`);
      }

      const data = await updateResponse.json();

      if (data.success) {
        setUploadStatus({
          success: true,
          message: "Video SEO updated successfully!"
        });
        
        // ✅ After successful YouTube update, also save to Firebase
        if (videoTitle) {
          await saveSEOToDB(user, videoTitle, seoData.title || title, seoData.description || description, 
                           seoData.tags || tags, seoData.keywords || keywords);
        }
      } else {
        setUploadStatus({
          success: false,
          message: data.error || "Failed to update video SEO"
        });
      }
    } catch (error) {
      console.error("Update error:", error);
      setUploadStatus({
        success: false,
        message: `An error occurred during update: ${error.message}`
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
            {displayVideo ? (
              <video src={displayVideo} controls className="preview-video" alt="Video Preview" />
            ) : (
              <img src={thumbnail} alt="Video Thumbnail" className="preview-image" />
            )}
          </div>

          <div className="customize-clip">
            <div className="seo-data">
              <div className="seo-box">
                <h2>Keywords</h2>
                <p>{keywords}</p>
              </div>
              <div className="seo-box">
                <h2>Description</h2>
                <div className="description-text">
                  {formatWithLineBreaks(description)}
                </div>
              </div>
              <div className="seo-box">
                <h2>Title</h2>
                <p>{title}</p>
              </div>
              <div className="seo-box">
                <h2>Tags</h2>
                <p>{tags}</p>
              </div>
            </div>

            <div className="action-buttons">
              {/* Compare Results Button */}
              <button
                className="comparison-btn"
                onClick={() =>
                  navigate("/comparison", {
                    state: {
                      results,
                      selectedFeatures,
                      videoURL,
                      localVideoPath,
                      seoData: {
                        ...seoData,
                        original_title: seoData.original_title || title,
                        original_description: seoData.original_description || description,
                        original_tags: seoData.original_tags || seoData.tags,
                        original_keywords: seoData.original_keywords || seoData.keywords,
                      },
                    },
                  })
                }
              >
                Compare Results
              </button>

              {/* YouTube Update SEO Button */}
              {videoURL && videoURL.includes("youtube.com") && (
                <>
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
                      className={`youtube-update-seo-btn ${uploading ? 'uploading' : ''}`}
                      onClick={handleUpdateSEO}
                      disabled={uploading || !user || !hasYoutubeAuth}
                    >
                      {uploading ? "Updating..." : "Update YouTube SEO"}
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Upload Status Message */}
            {uploadStatus && (
              <div className={`upload-status ${uploadStatus.success ? 'success' : 'error'}`}>
                <p>{uploadStatus.message}</p>
              </div>
            )}

            {/* YouTube Authorization Message */}
            {user && !hasYoutubeAuth && videoURL && videoURL.includes("youtube.com") && !authorizing && (
              <div className="youtube-auth-note">
                <p>
                  <strong>Note:</strong> To update SEO for YouTube videos, you need to connect 
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

export default SEO;