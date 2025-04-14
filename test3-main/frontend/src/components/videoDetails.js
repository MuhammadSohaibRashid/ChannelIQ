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
  // Add more feature icons as needed
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

// Helper function to safely extract values from potentially nested/complex objects
const safelyGetValue = (obj, defaultValue = "N/A") => {
  if (!obj) return defaultValue;
  
  if (typeof obj === 'object') {
    // If it's an array, join values
    if (Array.isArray(obj)) {
      return obj.length > 0 ? obj.join(", ") : defaultValue;
    }
    // If it's an object but not an array, join its values
    return Object.values(obj).length > 0 ? Object.values(obj).join(", ") : defaultValue;
  }
  
  // Return the value directly if it's a string or other primitive
  return obj || defaultValue;
};

const VideoDetails = ({ onClose, videoTitle }) => {
  const { user } = useContext(UserContext);
  const [video, setVideo] = useState(null); // Will hold { base: {}, longForm: {}, shortForm: {} }
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("optimization");
  const location = useLocation();
  const [activeFormType, setActiveFormType] = useState("longForm");
  const [error, setError] = useState(null);
  const [generatedClips, setGeneratedClips] = useState([]);


  // --- Data Fetching Effect ---
  useEffect(() => {
    const fetchVideoDetails = async () => {
      if (!user || !user.uid || !videoTitle) {
        console.error("User, UID, or Video Title is missing for fetching.");
        setError("Missing required information to fetch video details.");
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        // Ensure sanitization logic matches EXACTLY how IDs are created
        const sanitizedTitle = videoTitle.replace(/[^\w\s-]/gi, "").trim(); // Allow letters, numbers, space, hyphen

        const baseRef = doc(db, "users", user.uid, "videos", sanitizedTitle);
        const longFormRef = doc(db, "users", user.uid, "videos", sanitizedTitle, "generate", "LongForm");
        const shortFormRef = doc(db, "users", user.uid, "videos", sanitizedTitle, "generate", "ShortForm");

        console.log(`Fetching data for paths:
          Base: ${baseRef.path}
          Long Form: ${longFormRef.path}
          Short Form: ${shortFormRef.path}`);

        const [baseSnap, longSnap, shortSnap] = await Promise.all([
          getDoc(baseRef),
          getDoc(longFormRef),
          getDoc(shortFormRef)
        ]);

        if (!baseSnap.exists()) {
          console.error("Base video document not found:", baseRef.path);
          setError(`Video document not found at path: ${baseRef.path}`);
          setVideo(null);
        } else {
          const videoData = {
            base: baseSnap.data(),
            longForm: longSnap.exists() ? longSnap.data() : null,
            shortForm: shortSnap.exists() ? shortSnap.data() : null
          };
          console.log("Retrieved video data:", videoData);
          setVideo(videoData);

          // Extract generated clips from shortForm data if available
          if (videoData.shortForm && videoData.shortForm.clips && Array.isArray(videoData.shortForm.clips)) {
            setGeneratedClips(videoData.shortForm.clips);
            console.log("Found generated clips:", videoData.shortForm.clips);
          }

          // Set initial activeFormType based on available data
          if (videoData.longForm) {
            setActiveFormType("longForm");
          } else if (videoData.shortForm) {
            setActiveFormType("shortForm");
          }
          
          // Set initial tab based on available data
          if (videoData.longForm?.seo || videoData.shortForm?.seo) {
            // If SEO data is available, we can start with SEO tab
            const hasSEOFeature = 
              (videoData.longForm?.selectedFeatures || []).some(f => f.toLowerCase() === 'seo') ||
              (videoData.shortForm?.selectedFeatures || []).some(f => f.toLowerCase() === 'seo');
            
            if (hasSEOFeature) {
              setActiveTab("seo");
            }
          }
        }

      } catch (error) {
        console.error("Error fetching video details:", error);
        setError(`Failed to fetch video details: ${error.message}`);
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
        <div className="loading-spinner">
        <div className="spinner-dot"></div>
        <div className="spinner-dot"></div>
        <div className="spinner-dot"></div>
      </div>
          <p>Loading video details...</p>
        </div>
      </div>
    );
  }

  // --- Error State ---
  if (error || !video || !video.base) {
    return (
      <div className="modal-overlay">
        <div className="video-details-modal error-state">
          <h2>Error</h2>
          <p>{error || "Video details not found."}</p>
          <button className="close-button" onClick={handleClose}>Close</button>
        </div>
      </div>
    );
  }

  // --- Data Loaded - Destructure ---
  const { base, longForm, shortForm } = video;

  // --- Determine Data Source Based on Active Tab ---
  const currentFormData = activeFormType === "longForm" ? longForm : shortForm;
  const currentFormExists = !!currentFormData;
  
  // --- Extract data safely ---
  // For Long Form
  const longFormVideoUrl = longForm?.OptimizedVid?.s3?.url || null;
  const longFormSeoTitle = safelyGetValue(longForm?.seo?.title, base.title || "Untitled");
  const longFormSeoDescription = safelyGetValue(longForm?.seo?.description, base.description || "N/A");
  const longFormSeoKeywords = safelyGetValue(longForm?.seo?.keywords, "N/A");
  const longFormSeoTags = safelyGetValue(longForm?.seo?.tags, "N/A");
  
  // For Short Form
  const shortFormVideoUrl = shortForm?.OptimizedVid?.final_processed?.s3_url || null;
  const shortFormSeoTitle = safelyGetValue(shortForm?.seo?.title, base.title ? `${base.title} - Short` : "Untitled Short");
  const shortFormSeoDescription = safelyGetValue(shortForm?.seo?.description, base.description || "N/A");
  const shortFormSeoKeywords = safelyGetValue(shortForm?.seo?.keywords, "N/A");
  const shortFormSeoTags = safelyGetValue(shortForm?.seo?.tags, "N/A");
  
  // Processed Date
  const processedDateDisplay = currentFormData?.timestamp
    ? formatFirestoreTimestamp(currentFormData.timestamp)
    : "Not Available";
  
  // Enhancement Type
  const enhancementTypeDisplay = currentFormData?.OptimizedVid?.enhancementType || 
                               (currentFormData?.selectedFeatures?.includes("enhancement") ? "Standard Enhancement" : "N/A");
  
  // Status Handling
  let statusDisplay = "Unknown";
  let isOptimized = false;
  let processingStatusBadge = "Pending";
  
  // Different status paths for long form vs short form
  if (activeFormType === "longForm") {
    const rawStatus = longForm?.OptimizedVid?.emailNotification?.status || "pending";
    
    if (rawStatus === "success" || longFormVideoUrl) {
      statusDisplay = "Completed";
      isOptimized = true;
      processingStatusBadge = "Complete";
    } else if (rawStatus === "processing") {
      statusDisplay = "Processing";
      processingStatusBadge = "Processing";
    } else if (rawStatus === "failed") {
      statusDisplay = "Failed";
      processingStatusBadge = "Failed";
    } else {
      statusDisplay = "Pending email notification";
      processingStatusBadge = "Pending";
    }
  } else {
    // Short form status handling
    const rawStatus = shortForm?.OptimizedVid?.final_processed?.status;
    
    if (rawStatus === "success" || shortFormVideoUrl) {
      statusDisplay = "Completed";
      isOptimized = true;
      processingStatusBadge = "Complete";
    } else if (rawStatus === "processing") {
      statusDisplay = "Processing";
      processingStatusBadge = "Processing";
    } else if (rawStatus === "failed") {
      statusDisplay = "Failed";
      processingStatusBadge = "Failed";
    } else {
      statusDisplay = "Pending email notification";
      processingStatusBadge = "Pending";
    }
  }
  
  // Selected Features
  const selectedFeaturesForCurrentForm = currentFormData?.selectedFeatures || [];

  // Convert features to lowercase for consistent comparison
  const lowerCaseFeatures = selectedFeaturesForCurrentForm.map(f => f.toLowerCase());
  const hasSeoFeature = lowerCaseFeatures.includes('seo');

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
                ) : ( "N/A" )}
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
          {/* Show SEO tab only if SEO is in the selected features */}
          {hasSeoFeature && (
            <button
              className={`tab-button ${activeTab === "seo" ? "active" : ""}`}
              onClick={() => setActiveTab("seo")}
            >
              SEO
            </button>
          )}
          {/* Add Clips tab if clips are available */}
          {generatedClips.length > 0 && (
            <button
              className={`tab-button ${activeTab === "clips" ? "active" : ""}`}
              onClick={() => setActiveTab("clips")}
            >
              Clips
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
                    {longFormVideoUrl ? (
                      <video className="video-preview" controls src={longFormVideoUrl} poster={base.thumbnailUrl}>
                        Your browser does not support video playback.
                      </video>
                    ) : (
                      <div className="processing-placeholder">
                        <div className="loading-spinner"></div>
                        <p>Processing long-form video...</p>
                      </div>
                    )}
                    {longFormVideoUrl && (
                      <div className="video-download">
                        <a href={longFormVideoUrl} download target="_blank" rel="noopener noreferrer">
                          Download Long-Form
                        </a>
                      </div>
                    )}
                  </div>
                  <div className="optimization-details">
                    <h3>Long-Form Details</h3>
                    <div className="info-grid">
                      <div className="info-item">
                        <strong>Title:</strong>
                        <p>{longFormSeoTitle}</p>
                      </div>

                      <div className="info-item">
                        <strong>Description:</strong>
                        <p>{longFormSeoDescription}</p>
                      </div>

                      <div className="info-item">
                        <strong>Keywords:</strong>
                        <p>{longFormSeoKeywords}</p>
                      </div>
                      
                      <div className="info-item">
                        <strong>Tags:</strong>
                        <p>{longFormSeoTags}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Short Form Optimization Content */}
              {activeFormType === "shortForm" && shortForm && (
                <div className="form-type-content">
                  <div className="video-player-section">
                    <h3>Optimized Short-Form Video</h3>
                    {shortFormVideoUrl ? (
                      <video
                        className="video-preview vertical"
                        controls
                        src={shortFormVideoUrl}
                        poster={shortForm.thumbnail || base.thumbnailUrl}
                      >
                        Your browser does not support video playback.
                      </video>
                    ) : (
                      <div className="processing-placeholder">
                        <div className="loading-spinner"></div>
                        <p>Processing short-form video...</p>
                      </div>
                    )}
                    {shortFormVideoUrl && (
                      <div className="video-download">
                        <a
                          href={shortFormVideoUrl}
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
                      <div className="info-item">
                        <strong>Title:</strong>
                        <p>{shortFormSeoTitle}</p>
                      </div>
                      <div className="info-item">
                        <strong>Description:</strong>
                        <p>{shortFormSeoDescription}</p>
                      </div>
                      <div className="info-item">
                        <strong>Keywords:</strong>
                        <p>{shortFormSeoKeywords}</p>
                      </div>
                      <div className="info-item">
                        <strong>Tags:</strong>
                        <p>{shortFormSeoTags}</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Legacy Clips Section (from base) */}
              {base.processedClipPaths && base.processedClipPaths.length > 0 && (
                <div className="clips-section">
                  <h3>Generated Clips</h3>
                  <div className="clips-grid">
                    {base.processedClipPaths.map((clipPath, index) => (
                      <div key={index} className="clip-item">
                        <h4>Clip {index + 1}</h4>
                        <video className="clip-preview" controls src={clipPath}>
                          Video not supported.
                        </video>
                        <a href={clipPath} download target="_blank" rel="noopener noreferrer">
                          Download Clip
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )} {/* End Optimization Tab */}

          {/* --- SEO Tab --- */}
          {activeTab === "seo" && hasSeoFeature && (
            <div className="seo-tab">
              {/* Form Type Sub-Tabs */}
              <div className="form-type-tabs">
                {longForm && longForm.seo && ( // Only show tab if longForm data with SEO exists
                  <button
                    className={`form-type-button ${activeFormType === "longForm" ? "active" : ""}`}
                    onClick={() => setActiveFormType("longForm")}
                    disabled={!longForm || !longForm.seo}
                  >
                    Long Form SEO
                  </button>
                )}
                {shortForm && shortForm.seo && ( // Only show tab if shortForm data with SEO exists
                  <button
                    className={`form-type-button ${activeFormType === "shortForm" ? "active" : ""}`}
                    onClick={() => setActiveFormType("shortForm")}
                    disabled={!shortForm || !shortForm.seo}
                  >
                    Short Form SEO
                  </button>
                )}
              </div>

              {/* Long Form SEO Content */}
              {activeFormType === "longForm" && longForm?.seo && (
                <div className="form-type-content">
                  <h3>Long-Form SEO Details</h3>
                  <div className="seo-details info-grid">
                    <div className="info-item">
                      <strong>Title:</strong>
                      <p>{longFormSeoTitle}</p>
                    </div>
                    <div className="info-item">
                      <strong>Description:</strong>
                      <p>{longFormSeoDescription}</p>
                    </div>
                    <div className="info-item">
                      <strong>Keywords:</strong>
                      <p>{longFormSeoKeywords}</p>
                    </div>
                    <div className="info-item full-width">
                      <strong>Tags:</strong>
                      <div className="tags-container">
                        {typeof longForm.seo.tags === 'string' ? (
                          <p>{longForm.seo.tags}</p>
                        ) : Array.isArray(longForm.seo.tags) && longForm.seo.tags.length > 0 ? (
                          longForm.seo.tags.map((tag, index) => (
                            <span key={index} className="tag">{tag}</span>
                          ))
                        ) : (
                          <p>No tags specified.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Short Form SEO Content */}
              {activeFormType === "shortForm" && shortForm?.seo && (
                <div className="form-type-content">
                  <h3>Short-Form SEO Details</h3>
                  <div className="seo-details info-grid">
                    <div className="info-item">
                      <strong>Caption:</strong>
                      <p>{shortForm.seo?.caption || shortForm.caption || "N/A"}</p>
                    </div>
                    <div className="info-item">
                      <strong>Hashtags:</strong>
                      <p>{shortForm.seo?.hashtags || shortForm.hashtags || "N/A"}</p>
                    </div>
                    <div className="info-item full-width">
                      <strong>Trending Topics:</strong>
                      <div className="tags-container">
                        {Array.isArray(shortForm.seo?.trendingTopics) && shortForm.seo.trendingTopics.length > 0 ? (
                          shortForm.seo.trendingTopics.map((topic, index) => (
                            <span key={index} className="tag trending">{topic}</span>
                          ))
                        ) : (
                          <p>No trending topics specified.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )} {/* End SEO Tab */}

          {/* --- Clips Tab --- */}
          {activeTab === "clips" && generatedClips.length > 0 && (
            <div className="clips-tab">
              <h3>Generated Short-Form Clips</h3>
              <div className="clips-info">
                <div className="info-item">
                  <strong>Clip Count:</strong> {shortForm?.clipCount || generatedClips.length}
                </div>
                <div className="info-item">
                  <strong>Clip Length:</strong> {shortForm?.clipLength || "60"} seconds
                </div>
                <div className="info-item">
                  <strong>Status:</strong> {shortForm?.status || "Success"}
                </div>
              </div>
              <div className="clips-grid">
                {generatedClips.map((clip, index) => (
                  <div key={index} className="clip-item">
                    <h4>Clip {index + 1}</h4>
                    <video className="clip-preview vertical" controls src={clip.url}>
                      Video not supported.
                    </video>
                    <div className="clip-actions">
                      <a href={clip.url} download target="_blank" rel="noopener noreferrer" className="download-button">
                        Download Clip
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )} {/* End Clips Tab */}
        </div> {/* End tab-content */}
      </div> {/* End video-details-modal */}
    </div> // End modal-overlay
  );
};

export default VideoDetails;