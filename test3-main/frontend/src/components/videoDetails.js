import React, { useEffect, useState, useContext, useCallback } from "react";
import { doc, getDoc } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import "./videoDetails.css";
import { useLocation } from "react-router-dom";

// Single definition of featureIcons using emojis
const featureIcons = {
  seo: "🔍",
  transcription: "📝",
  subtitles: "💬",
  editing: "✂️",
  enhancement: "✨",
  noisereduction: "🔉",
  videoquality: "🎬",
  captions: "💬",
  // Add more feature icons corresponding to potential values in 'selectedFeatures'
};

// Helper function to format Firebase Timestamp
const formatFirestoreTimestamp = (timestamp) => {
  if (!timestamp || typeof timestamp.seconds !== 'number') {
    return "N/A"; // Return Not Applicable or Processing
  }
  try {
    return new Date(timestamp.seconds * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch (e) {
    console.error("Error formatting timestamp:", e);
    return "Invalid Date";
  }
};

const VideoDetails = ({ onClose }) => {
  const { user } = useContext(UserContext);
  const [video, setVideo] = useState(null); // Will hold { base: {}, longForm: {}, shortForm: {} }
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("optimization");
  const location = useLocation();
  // Default to longForm only if longForm data might exist, otherwise check shortForm
  const [activeFormType, setActiveFormType] = useState("longForm");

  // Get videoTitle from location state
  const videoTitle = location.state?.videoTitle;

  // --- Data Fetching Effect ---
  useEffect(() => {
    const fetchVideoDetails = async () => {
      if (!user || !user.uid || !videoTitle) {
        console.error("User, UID, or Video Title is missing for fetching.", { user, uid: user?.uid, videoTitle });
        setLoading(false);
        return;
      }

      console.log("Fetching video details for:", { uid: user.uid, videoTitle });
      setLoading(true);
      try {
        // Use the exact videoTitle for path (no need to sanitize if that's how it's stored)
        const metadataRef = doc(db, "users", user.uid, "videos", videoTitle, "fetchedVideos", "metadata");
        const longFormRef = doc(db, "users", user.uid, "videos", videoTitle, "generate", "LongForm");
        const shortFormRef = doc(db, "users", user.uid, "videos", videoTitle, "generate", "ShortForm");

        console.log("Fetching from paths:", {
          metadataPath: metadataRef.path,
          longFormPath: longFormRef.path,
          shortFormPath: shortFormRef.path
        });

        const [metadataSnap, longSnap, shortSnap] = await Promise.all([
          getDoc(metadataRef),
          getDoc(longFormRef),
          getDoc(shortFormRef)
        ]);

        // Log what we received
        console.log("Metadata exists:", metadataSnap.exists());
        console.log("LongForm exists:", longSnap.exists());
        console.log("ShortForm exists:", shortSnap.exists());

        if (metadataSnap.exists()) {
          console.log("Metadata data:", metadataSnap.data());
        }
        if (longSnap.exists()) {
          console.log("LongForm data:", longSnap.data());
        }
        if (shortSnap.exists()) {
          console.log("ShortForm data:", shortSnap.data());
        }

        if (!metadataSnap.exists()) {
          console.error("Metadata document not found:", metadataRef.path);
          setVideo(null);
        } else {
          const videoData = {
            base: metadataSnap.data(),
            longForm: longSnap.exists() ? longSnap.data() : null,
            shortForm: shortSnap.exists() ? shortSnap.data() : null
          };
          console.log("Combined video data:", videoData);
          setVideo(videoData);

          // Set initial activeFormType based on available data
          if (videoData.longForm) {
            setActiveFormType("longForm");
          } else if (videoData.shortForm) {
            setActiveFormType("shortForm");
          }
        }

      } catch (error) {
        console.error("Error fetching video details:", error);
        setVideo(null);
      } finally {
        setLoading(false);
      }
    };

    fetchVideoDetails();
  }, [user, videoTitle]);

  // --- Modal Close Handling ---
  const handleClose = useCallback(() => {
    if (onClose && typeof onClose === 'function') {
      onClose();
    }
  }, [onClose]);

  // Effect for Escape key and body scroll lock
  useEffect(() => {
    const handleEscKey = (event) => {
      if (event.key === 'Escape') {
        handleClose();
      }
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleEscKey);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleEscKey);
    };
  }, [handleClose]);

  // --- Loading State ---
  if (loading) {
    return (
      <div className="modal-overlay">
        <div className="video-details-modal loading-state">
          <div className="loading-spinner"></div> <p>Loading...</p>
        </div>
      </div>
    );
  }

  // --- Error or Not Found State ---
  if (!video || !video.base) {
    return (
      <div className="modal-overlay">
        <div className="video-details-modal error-state">
          <h2>Error</h2>
          <p>Video details not found.</p>
          <button onClick={handleClose}>Close</button>
        </div>
      </div>
    );
  }

  // --- Data Loaded - Destructure ---
  const { base, longForm, shortForm } = video;

  // --- Determine Data Source Based on Active Tab ---
  const currentFormData = activeFormType === "longForm" ? longForm : shortForm;
  const currentFormExists = !!currentFormData; // Check if the active form data object exists

  // --- Dynamic Meta Values ---
  const processedDateDisplay = formatFirestoreTimestamp(currentFormData?.timestamp || currentFormData?.processedDate);
  const enhancementTypeDisplay = currentFormData?.enhancementType || "N/A"; 
  // Adjust status logic to check both status and uppercase SUCCESS
  const statusDisplay = currentFormData?.status || "Unknown"; 
  const isOptimized = statusDisplay.toLowerCase() === "completed" || statusDisplay.toLowerCase() === "success"; 
  const processingStatusBadge = isOptimized ? "Complete" : (statusDisplay.toLowerCase() === "processing" ? "Processing" : "Pending");
  
  // Get selected features - accounting for both array and lowercase "noisereduction" format
  let selectedFeaturesForCurrentForm = [];
  if (currentFormData?.selectedFeatures && Array.isArray(currentFormData.selectedFeatures)) {
    selectedFeaturesForCurrentForm = currentFormData.selectedFeatures.map(feature => 
      typeof feature === 'string' ? feature : String(feature)
    );
  }
  
  console.log("Render data:", {
    processedDateDisplay,
    enhancementTypeDisplay,
    statusDisplay,
    isOptimized,
    processingStatusBadge,
    selectedFeaturesForCurrentForm,
    activeFormType
  });

  // Helper to get the correct video URL for the short form
  const getShortFormVideoUrl = () => {
    if (!shortForm) return null;
    
    // Direct URL if available
    if (shortForm.processedVideoURL) return shortForm.processedVideoURL;
    
    // Check processed clips if available
    if (shortForm.processedClips && shortForm.processedClips.length > 0) {
      return shortForm.processedClips[0].url;
    }
    
    // Check clip path directly
    if (shortForm.clipPath) return shortForm.clipPath;
    
    return null;
  };

  // --- Render Main Modal ---
  return (
    <div
      className="modal-overlay"
      onClick={(e) => e.target.className === 'modal-overlay' && handleClose()}
    >
      <div className="video-details-modal">
        {/* --- Header --- */}
        <div className="modal-header">
          <h2>{base.title || "Untitled Video"}</h2>
          <button className="close-button" onClick={handleClose} aria-label="Close">
            <span className="close-icon">×</span>
          </button>
        </div>

        {/* --- Preview Header --- */}
        <div className="video-preview-header">
          <div className="video-thumbnail-container">
            <img
              src={base.thumbnailUrl || "/images/fallback-thumbnail.jpg"}
              alt={base.title || "Video thumbnail"}
              className="video-thumbnail"
            />
            <div className={`status-badge ${isOptimized ? 'complete' : 'processing'}`}>
              {processingStatusBadge}
            </div>
            {/* Show Long/Short Form type badge if data exists */}
            {currentFormExists && (
              <div className="type-badge">{activeFormType === "longForm" ? "Long Form" : "Short Form"}</div>
            )}
          </div>

          <div className="video-meta">
            {/* Row 1: Processed Date, Enhancement */}
            <div className="meta-row">
              <div className="meta-item">
                <strong>Processed on:</strong> {processedDateDisplay}
              </div>
              <div className="meta-item">
                <strong>Enhancement:</strong> {enhancementTypeDisplay}
              </div>
            </div>

            {/* Row 2: Original Source, Status Text */}
            <div className="meta-row">
              <div className="meta-item">
                <strong>Original Source:</strong>
                {base.videoURL ? (
                  <a href={base.videoURL} target="_blank" rel="noopener noreferrer" className="source-link">View Original</a>
                ) : (
                  "N/A"
                )}
              </div>
              <div className="meta-item">
                <strong>Status:</strong>
                <span className={isOptimized ? "status-complete" : "status-processing"}>
                  {statusDisplay.charAt(0).toUpperCase() + statusDisplay.slice(1)} {/* Capitalize status */}
                </span>
              </div>
            </div>

            {/* Row 3: Selected Features for Current Form Type */}
            {selectedFeaturesForCurrentForm.length > 0 && (
              <div className="meta-row">
                <div className="meta-item full-width">
                  <strong>Selected Features ({activeFormType === "longForm" ? "Long" : "Short"}):</strong>
                  <div className="feature-badges">
                    {selectedFeaturesForCurrentForm.map(feature => (
                      <span key={feature} className="feature-badge">
                        <span className="feature-icon">{featureIcons[feature.toLowerCase()] || "⚙️"}</span>
                        <span>{feature}</span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* --- Tabs --- */}
        <div className="modal-tabs">
          <button
            className={`tab-button ${activeTab === "optimization" ? "active" : ""}`}
            onClick={() => setActiveTab("optimization")}
          >
            Optimization
          </button>
          {/* Show SEO tab only if SEO is in the selected features for the *currently active* form type or if seo data exists */}
          {(selectedFeaturesForCurrentForm.some(f => f.toLowerCase() === 'seo') || currentFormData?.seo) && (
            <button
              className={`tab-button ${activeTab === "seo" ? "active" : ""}`}
              onClick={() => setActiveTab("seo")}
            >
              SEO
            </button>
          )}
        </div>

        {/* --- Tab Content --- */}
        <div className="tab-content">
          {/* --- Optimization Tab --- */}
          {activeTab === "optimization" && (
            <div className="optimization-tab">
              {/* Form Type Sub-Tabs */}
              <div className="form-type-tabs">
                {longForm && ( // Only show tab if longForm data exists
                  <button
                    className={`form-type-button ${activeFormType === "longForm" ? "active" : ""}`}
                    onClick={() => setActiveFormType("longForm")}
                    disabled={!longForm} // Disable if no long form data
                  >
                    Long Form
                  </button>
                )}
                {shortForm && ( // Only show tab if shortForm data exists
                  <button
                    className={`form-type-button ${activeFormType === "shortForm" ? "active" : ""}`}
                    onClick={() => setActiveFormType("shortForm")}
                    disabled={!shortForm} // Disable if no short form data
                  >
                    Short Form
                  </button>
                )}
              </div>

              {/* Long Form Optimization Content */}
              {activeFormType === "longForm" && longForm && (
                <div className="form-type-content">
                  <div className="video-player-section">
                    <h3>Optimized Long-Form Video</h3>
                    {(longForm.processedVideoURL || longForm.s3FinalURL || longForm.processedURL) ? (
                      <video 
                        className="video-preview" 
                        controls 
                        src={longForm.processedVideoURL || longForm.s3FinalURL || longForm.processedURL} 
                        poster={base.thumbnailUrl}
                      >
                        Your browser does not support video playback.
                      </video>
                    ) : (
                      <div className="processing-placeholder"><div className="loading-spinner"></div><p>Processing long-form video...</p></div>
                    )}
                    {(longForm.processedVideoURL || longForm.s3FinalURL || longForm.processedURL) && (
                      <div className="video-download">
                        <a 
                          href={longForm.processedVideoURL || longForm.s3FinalURL || longForm.processedURL} 
                          download 
                          target="_blank" 
                          rel="noopener noreferrer"
                        >
                          Download Long-Form
                        </a>
                      </div>
                    )}
                  </div>
                  <div className="optimization-details">
                    <h3>Long-Form Details</h3>
                    <div className="info-grid">
                      <div className="info-item"><strong>Title:</strong><p>{longForm.title || base.title || "Untitled"}</p></div>
                      <div className="info-item"><strong>Description:</strong><p>{longForm.description || longForm.seo?.description || base.description || "N/A"}</p></div>
                      <div className="info-item"><strong>Keywords:</strong><p>{longForm.keywords || longForm.seo?.keywords || base.keywords || "N/A"}</p></div>
                    </div>
                  </div>
                </div>
              )}

              {/* Short Form Optimization Content */}
              {activeFormType === "shortForm" && shortForm && (
                <div className="form-type-content">
                  <div className="video-player-section">
                    <h3>Optimized Short-Form Video</h3>
                    {getShortFormVideoUrl() ? (
                      <video 
                        className="video-preview vertical" 
                        controls 
                        src={getShortFormVideoUrl()} 
                        poster={shortForm.thumbnail || base.thumbnailUrl}
                      >
                        Your browser does not support video playback.
                      </video>
                    ) : (
                      <div className="processing-placeholder"><div className="loading-spinner"></div><p>Processing short-form video...</p></div>
                    )}
                    {getShortFormVideoUrl() && (
                      <div className="video-download">
                        <a 
                          href={getShortFormVideoUrl()} 
                          download 
                          target="_blank" 
                          rel="noopener noreferrer"
                        >
                          Download Short-Form
                        </a>
                      </div>
                    )}
                  </div>
                  <div className="optimization-details">
                    <h3>Short-Form Details</h3>
                    <div className="info-grid">
                      <div className="info-item"><strong>Title:</strong><p>{shortForm.title || base.title || "Untitled Short"}</p></div>
                      <div className="info-item"><strong>Caption:</strong><p>{shortForm.caption || "N/A"}</p></div>
                      <div className="info-item"><strong>Hashtags:</strong><p>{shortForm.hashtags || "N/A"}</p></div>
                    </div>
                  </div>
                </div>
              )}

              {/* Clips Section - Show if in the base or in the short form */}
              {(base.processedClipPaths && base.processedClipPaths.length > 0) || 
               (shortForm && shortForm.processedClips && shortForm.processedClips.length > 0) ? (
                <div className="clips-section">
                  <h3>Generated Clips</h3>
                  <div className="clips-grid">
                    {/* Show base clips if available */}
                    {base.processedClipPaths && base.processedClipPaths.length > 0 && 
                      base.processedClipPaths.map((clipPath, index) => (
                        <div key={`base-clip-${index}`} className="clip-item">
                          <h4>Clip {index + 1}</h4>
                          <video className="clip-preview" controls src={clipPath}> Video not supported. </video>
                          <a href={clipPath} download target="_blank" rel="noopener noreferrer">Download Clip</a>
                        </div>
                      ))
                    }
                    
                    {/* Show short form processed clips if available */}
                    {shortForm && shortForm.processedClips && shortForm.processedClips.length > 0 &&
                      shortForm.processedClips.map((clip, index) => (
                        <div key={`short-clip-${index}`} className="clip-item">
                          <h4>Short Clip {index + 1}</h4>
                          <video className="clip-preview" controls src={clip.url}> Video not supported. </video>
                          <a href={clip.url} download target="_blank" rel="noopener noreferrer">Download Clip</a>
                        </div>
                      ))
                    }
                  </div>
                </div>
              ) : null}
            </div>
          )} {/* End Optimization Tab */}

          {/* --- SEO Tab --- */}
          {activeTab === "seo" && (selectedFeaturesForCurrentForm.some(f => f.toLowerCase() === 'seo') || currentFormData?.seo) && (
            <div className="seo-tab">
              {/* Form Type Sub-Tabs */}
              <div className="form-type-tabs">
                {longForm && longForm.seo && ( // Only show tab if longForm data exists AND SEO data exists
                  <button
                    className={`form-type-button ${activeFormType === "longForm" ? "active" : ""}`}
                    onClick={() => setActiveFormType("longForm")}
                    disabled={!longForm || !longForm.seo}
                  >
                    Long Form SEO
                  </button>
                )}
                {shortForm && (shortForm.seo || shortForm.seo_details) && ( // Only show tab if shortForm data exists AND SEO data exists
                  <button
                    className={`form-type-button ${activeFormType === "shortForm" ? "active" : ""}`}
                    onClick={() => setActiveFormType("shortForm")}
                    disabled={!shortForm || (!shortForm.seo && !shortForm.seo_details)}
                  >
                    Short Form SEO
                  </button>
                )}
              </div>

              {/* Long Form SEO Content */}
              {activeFormType === "longForm" && longForm?.seo && (
                <div className="form-type-content">
                  <h3>Long-Form SEO Details</h3>
                  <div className="seo-details info-grid"> {/* Re-use info-grid styling */}
                    <div className="info-item"><strong>Title:</strong><p>{longForm.seo.title || longForm.title || base.title || "N/A"}</p></div>
                    <div className="info-item"><strong>Description:</strong><p>{longForm.seo.description || longForm.description || base.description || "N/A"}</p></div>
                    <div className="info-item"><strong>Keywords:</strong><p>{longForm.seo.keywords || longForm.keywords || "N/A"}</p></div>
                    <div className="info-item full-width"> {/* Make tags take full width */}
                      <strong>Tags:</strong>
                      <div className="tags-container">
                        {longForm.seo.tags ? (
                          // Handle array tags
                          Array.isArray(longForm.seo.tags) ? 
                            longForm.seo.tags.map(tag => <span key={tag} className="tag">{tag}</span>) :
                            // Handle string tags (comma separated)
                            longForm.seo.tags.split(",").map(tag => <span key={tag.trim()} className="tag">{tag.trim()}</span>)
                        ) : (
                          <p>No tags specified.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Short Form SEO Content */}
              {activeFormType === "shortForm" && (shortForm?.seo || shortForm?.seo_details) && (
                <div className="form-type-content">
                  <h3>Short-Form SEO Details</h3>
                  <div className="seo-details info-grid">
                    {/* Use shortForm.seo if available, else fall back to shortForm.seo_details */}
                    {(() => {
                      const seoData = shortForm.seo || shortForm.seo_details || {};
                      return (
                        <>
                          <div className="info-item">
                            <strong>Caption:</strong>
                            <p>{seoData.caption || shortForm.caption || "N/A"}</p>
                          </div>
                          <div className="info-item">
                            <strong>Hashtags:</strong>
                            <p>{seoData.hashtags || shortForm.hashtags || "N/A"}</p>
                          </div>
                          <div className="info-item full-width">
                            <strong>Trending Topics:</strong>
                            <div className="tags-container">
                              {seoData.trendingTopics ? (
                                Array.isArray(seoData.trendingTopics) ?
                                  seoData.trendingTopics.map(topic => <span key={topic} className="tag trending">{topic}</span>) :
                                  seoData.trendingTopics.split(",").map(topic => <span key={topic.trim()} className="tag trending">{topic.trim()}</span>)
                              ) : (
                                <p>No trending topics specified.</p>
                              )}
                            </div>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>
          )} {/* End SEO Tab */}
        </div> {/* End tab-content */}
      </div> {/* End video-details-modal */}
    </div> // End modal-overlay
  );
};

export default VideoDetails;