import React, { useEffect, useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { db } from "../Firebase";
import { collection, getDocs, serverTimestamp, doc, setDoc } from "firebase/firestore";
import { UserContext } from "./UserContext";
import "./clippreview.css";

function ClipPreview() {
    const { user, logout } = useContext(UserContext);
    const location = useLocation();
    const navigate = useNavigate();
    const { clipPaths = [], videoURL = null, videoTitle = null } = location.state || {};
    const [error, setError] = useState(null);
    const [processedClips, setProcessedClips] = useState([]);
    const [selectedClip, setSelectedClip] = useState(null);
    const [selectedFeatures, setSelectedFeatures] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('clips');
    
    // Function to save clip details to Firebase
    const saveClipDataToFirebase = async (clipPath, features, videoTitle) => {
        if (!user) {
            console.log("User not logged in. Cannot save clip data.");
            return;
        }
    
        try {
            const videosRef = collection(db, "users", user.uid, "videos");
            const querySnapshot = await getDocs(videosRef);
    
            let sanitizedTitle = videoTitle 
                ? videoTitle.replace(/[^\w\s-]/gi, "").trim()
                : null;
    
            let originalTitle = videoTitle || null;
    
            if (!sanitizedTitle) {
                querySnapshot.forEach((doc) => {
                    const videoData = doc.data();
                    
                    if (videoData.title) {
                        let title = videoData.title.replace(/[^\w\s-]/gi, "").trim();
                        
                        if (!sanitizedTitle) {
                            sanitizedTitle = title;
                            originalTitle = videoData.title;
                        }
                    }
                });
            }
    
            if (!sanitizedTitle) {
                sanitizedTitle = `video_${Date.now()}`;
                originalTitle = "Unknown Video"; 
            }
    
            const clipDocRef = doc(db, `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`);
    
            await setDoc(clipDocRef, {
                clipPath: clipPath.url || clipPath,
                clipKey: clipPath.key || clipPath,
                selectedFeatures: features,
                processedClips: processedClips || [],
                timestamp: serverTimestamp(),
                videoTitle: originalTitle,
                videoURL: videoURL,
            });
    
            console.log("Clip details saved successfully!");
        } catch (error) {
            console.error("Error saving clip data:", error);
        }
    };

    useEffect(() => {
        if (!clipPaths || clipPaths.length === 0) {
            setError("No clips found to display.");
        } else {
            // Handle the new S3 format
            const clips = clipPaths.map(clip => {
                // Check if the clip is an object with url and key properties (S3 format)
                if (typeof clip === 'object' && clip.url) {
                    return {
                        url: clip.url,
                        key: clip.key
                    };
                } else {
                    // Fallback for older format (local path)
                    return {
                        url: `http://127.0.0.1:8000/media/${clip}`,
                        key: clip
                    };
                }
            });
    
            setProcessedClips(clips);
        }
    }, [clipPaths]);

    const handleClipSelection = (clip) => {
        setSelectedClip(selectedClip === clip ? null : clip);
    };

    const handleFeatureToggle = (feature) => {
        setSelectedFeatures((prevFeatures) =>
            prevFeatures.includes(feature)
                ? prevFeatures.filter((f) => f !== feature)
                : [...prevFeatures, feature]
        );
    };

    const handleOptimize = async () => {
        if (!selectedClip) {
            alert("Please select a clip to optimize.");
            return;
        }
    
        if (selectedFeatures.length === 0) {
            alert("Please select at least one feature to apply.");
            return;
        }
    
        setLoading(true);
    
        try {
            const videoTitle = location.state?.videoTitle || "Untitled Video";
    
            const isSEOIncluded = selectedFeatures.includes("SEO");
            const response = await fetch(`http://127.0.0.1:8000/api/optimize_shortform/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    clipPath: selectedClip.url,
                    clipKey: selectedClip.key,
                    selectedFeatures: selectedFeatures,
                    videoURL: videoURL,
                    userEmail: user?.email,
                    timestamp: serverTimestamp(),
                }),
            });
    
            if (response.ok) {
                const result = await response.json();
                
                // Check if there was a language detection error for captions
                if (result.results.captions && result.results.captions.status === "language_error") {
                    // Show alert about language limitation and stop processing
                    alert(`${result.results.captions.message} Processing cannot continue.`);
                    return; // Exit the function early
                }
                await saveClipDataToFirebase(selectedClip, selectedFeatures, videoTitle);
    
                if (isSEOIncluded) {
                    navigate("/seo_shortform", { 
                        state: { 
                            message: result.message, 
                            results: result.results, 
                            selectedFeatures, 
                            selectedClip,
                            videoTitle
                        } 
                    });
                } else {
                    navigate("/optimizevideo_shortform", { 
                        state: { 
                            message: result.message, 
                            results: result.results, 
                            selectedFeatures, 
                            selectedClip,
                            videoTitle
                        } 
                    });
                }
            } else {
                alert("An error occurred during optimization. Please try again.");
            }
        } catch (error) {
            console.error("Error during optimization:", error);
            alert("An error occurred. Please check your connection and try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleClipperClick = () => {
        navigate('/clipper');
    };

    const features = [
        { id: "NoiseReduction", name: "Noise Reduction", icon: "🔊" },
        { id: "VideoQuality", name: "Video Quality", icon: "🎬" },
        { id: "SEO", name: "SEO", icon: "🔍" },
        { id: "Captions", name: "Captions", icon: "💬" }
    ];

    return (
        <div className="dashboard-container">
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

            {/* Main Content */}
            <div className="dashboard-content">
                {/* Sidebar */}
                <div className="sidebar">
                    <div className="sidebar-header">
                        <h2>Dashboard</h2>
                    </div>
                    <nav className="sidebar-nav">
                        <button 
                            className={`sidebar-button ${activeTab === 'clips' ? 'active' : ''}`}
                            onClick={() => setActiveTab('clips')}
                        >
                            <span className="sidebar-icon">🎬</span>
                            <span>Clips</span>
                        </button>
                        <button 
                            className={`sidebar-button ${activeTab === 'features' ? 'active' : ''}`}
                            onClick={() => setActiveTab('features')}
                        >
                            <span className="sidebar-icon">⚙️</span>
                            <span>Features</span>
                        </button>
                       
                    </nav>
                </div>

                {/* Main Content Area */}
                <div className="main-area">
                    <div className="content-container">
                        <div className="content-header">
                            <h2 className="content-title">
                                {activeTab === 'clips' ? 'Your Viral Clips' : 'Optimization Features'}
                            </h2>
                        </div>

                        {/* Content Body */}
                        <div className="content-body">
                            {activeTab === 'clips' ? (
                                <div className="clips-container">
                                    {error ? (
                                        <div className="error-card">
                                            <p className="error-message">{error}</p>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="clips-grid-preview">
                                                {processedClips.map((clip, index) => (
                                                    <div 
                                                        key={index} 
                                                        className={`clip-card ${selectedClip === clip ? 'selected' : ''}`}
                                                        onClick={() => handleClipSelection(clip)}
                                                    >
                                                        <div className="clip-preview">
                                                            <video
                                                                src={clip.url}
                                                                controls
                                                                className="clip-videos"
                                                            />
                                                        </div>
                                                        
                                                    </div>
                                                ))}
                                            </div>
                                            
                                            
                                        </>
                                    )}
                                </div>
                            ) : (
                                <div className="features-container">
                                    <div className="features-grid">
                                        {features.map((feature) => (
                                            <div 
                                                key={feature.id} 
                                                className={`feature-card ${selectedFeatures.includes(feature.name) ? 'selected' : ''}`}
                                                onClick={() => handleFeatureToggle(feature.name)}
                                            >
                                                <div className="feature-icon-clips">{feature.icon}</div>
                                                <h3 className="feature-name">{feature.name}</h3>
                                                <div className="feature-selected-indicator">
                                                    {selectedFeatures.includes(feature.name) && (
                                                        <span className="selected-icon">✓</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Action Section */}
                        <div className="action-section">
                            <div className="action-container">
                                <div className="selected-items">
                                    <div className="selected-item">
                                        <span className="item-label">Selected Clip:</span>
                                        <span className="item-value">
                                            {selectedClip ? `Clip ${processedClips.indexOf(selectedClip) + 1}` : 'None'}
                                        </span>
                                    </div>
                                    <div className="selected-item">
                                        <span className="item-label">Selected Features:</span>
                                        <span className="item-value">
                                            {selectedFeatures.length > 0 
                                                ? selectedFeatures.join(', ') 
                                                : 'None'}
                                        </span>
                                    </div>
                                </div>
                                <button 
                                    className="optimize-button"
                                    onClick={handleOptimize}
                                    disabled={!selectedClip || selectedFeatures.length === 0 || loading}
                                >
                                    {loading ? "Processing..." : "Optimize"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ClipPreview;