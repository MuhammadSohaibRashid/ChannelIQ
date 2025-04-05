import React, { useEffect, useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { db } from "../Firebase"; // Make sure the Firebase config is correctly imported
import { collection, getDocs, serverTimestamp, doc, setDoc } from "firebase/firestore";
import { UserContext } from "./UserContext"; // Import User Context
import "./clippreview.css";

function ClipPreview() {
    const { user, logout } = useContext(UserContext); // Get user details from Context
    const location = useLocation();
    const navigate = useNavigate();
    const { clipPaths = [], videoURL = null, videoTitle = null } = location.state || {};
    const [error, setError] = useState(null);
    const [processedClips, setProcessedClips] = useState([]);
    const [selectedClip, setSelectedClip] = useState(null);
    const [selectedFeatures, setSelectedFeatures] = useState([]);
    const [loading, setLoading] = useState(false);

    // Function to save clip details to Firebase
    console.log("🎬 Received Video Title:", location.state?.videoTitle);

    const saveClipDataToFirebase = async (clipPath, features, videoTitle) => {
        console.log("🔄 saveClipDataToFirebase called");
        console.log("📽️ Incoming Video Title from Clipper Page:", videoTitle);
    
        if (!user) {
            console.log("❌ User not logged in. Cannot save clip data.");
            return;
        }
    
        try {
            console.log("🔍 Fetching videos for user:", user.uid);
            const videosRef = collection(db, "users", user.uid, "videos");
            const querySnapshot = await getDocs(videosRef);
    
            let sanitizedTitle = videoTitle 
                ? videoTitle.replace(/[^\w\s]/gi, "").trim() 
                : null;
    
            let originalTitle = videoTitle || null; // Store actual title
    
            console.log("🟢 Step 1: Initial Sanitized Title:", sanitizedTitle);
            console.log("🟢 Step 2: Original Video Title:", originalTitle);
    
            // Fetch title from Firestore if not provided
            if (!sanitizedTitle) {
                querySnapshot.forEach((doc) => {
                    const videoData = doc.data();
                    console.log("📌 Video Data from Firestore:", videoData);
    
                    if (videoData.title) {
                        let title = videoData.title.replace(/[^\w\s]/gi, "").trim();
                        console.log("✅ Found and Sanitized Title from Firestore:", title);
    
                        if (!sanitizedTitle) {
                            sanitizedTitle = title;
                            originalTitle = videoData.title;
                            console.log("🟢 Step 3: Updated Sanitized Title:", sanitizedTitle);
                            console.log("🟢 Step 4: Updated Original Title:", originalTitle);
                        }
                    }
                });
            }
    
            if (!sanitizedTitle) {
                console.log("⚠️ No matching video found for title. Using fallback.");
                sanitizedTitle = `video_${Date.now()}`;
                originalTitle = "Unknown Video"; 
            }
    
            console.log("📌 Received Video Title:", videoTitle);
            console.log("📌 Final Sanitized Video Title:", sanitizedTitle);
            console.log("✅ Firestore Path:", `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`);
    
            const clipDocRef = doc(db, `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`);
    
            await setDoc(clipDocRef, {
                clipPath: clipPath.url || clipPath, // Handle both clip object and string formats
                clipKey: clipPath.key || clipPath,  // Handle both clip object and string formats
                selectedFeatures: features,
                processedClips: processedClips || [],
                optimized: false,
                timestamp: serverTimestamp(),
                videoTitle: originalTitle, // Save original video title
                videoURL: videoURL // Add the videoURL
            });
    
            console.log("✅ Clip details saved successfully in Firestore!");
        } catch (error) {
            console.error("🔥 Error saving clip data to Firestore:", error);
        }
    };

    useEffect(() => {
        console.log("Received clips:", clipPaths);
    
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
    
            console.log("Processed clips:", clips);
            setProcessedClips(clips);
        }
    }, [clipPaths]);

    const handleClipSelection = (clip) => {
        console.log("📌 Clip selected:", clip);
        setSelectedClip(selectedClip === clip ? null : clip);
    };

    const handleFeatureToggle = (feature) => {
        console.log(`📌 Toggling feature: ${feature}`);
        setSelectedFeatures((prevFeatures) =>
            prevFeatures.includes(feature)
                ? prevFeatures.filter((f) => f !== feature)
                : [...prevFeatures, feature]
        );
    };

    const handleOptimize = async () => {
        if (!selectedClip) {
            alert("⚠️ Please select a clip to optimize.");
            return;
        }
    
        if (selectedFeatures.length === 0) {
            alert("⚠️ Please select at least one feature to apply.");
            return;
        }
    
        setLoading(true);
    
        console.log("🚀 Optimization started");
        console.log("🎯 Selected Clip:", selectedClip);
        console.log("🔍 Selected Features:", selectedFeatures);
    
        try {
            // Extract videoTitle from location.state
            const videoTitle = location.state?.videoTitle || "Untitled Video";
    
            console.log("📑 Video Title to be sent:", videoTitle);
    
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
                    videoURL: videoURL // Add the videoURL from state
                }),
            });
    
            if (response.ok) {
                const result = await response.json();
                console.log("✅ API result:", result);
    
                console.log("💾 Saving clip data after optimization...");
                await saveClipDataToFirebase(selectedClip, selectedFeatures, videoTitle);
    
                if (isSEOIncluded) {
                    console.log("🔄 Navigating to SEO Short Form page");
                    navigate("/seo_shortform", { 
                        state: { 
                            message: result.message, 
                            results: result.results, 
                            selectedFeatures, 
                            selectedClip,
                            videoTitle // Pass videoTitle
                        } 
                    });
                } else {
                    console.log("🔄 Navigating to Optimize Video Short Form page");
                    navigate("/optimizevideo_shortform", { 
                        state: { 
                            message: result.message, 
                            results: result.results, 
                            selectedFeatures, 
                            selectedClip,
                            videoTitle // Pass videoTitle
                        } 
                    });
                }
            } else {
                console.error("❌ API call failed:", response.statusText);
                alert("An error occurred during optimization. Please try again.");
            }
        } catch (error) {
            console.error("🔥 Error during optimization:", error);
            alert("An error occurred. Please check your connection and try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleClipperClick = () => {
        console.log("🔄 Navigating to /clipper");
        navigate('/clipper');
    };

    return (
        <div className="clipping-app">
            {/* 🔹 NAVBAR */}
            <header className="header">
                <h1 className="logo" onClick={() => navigate("/")}>
                    <span className="bold">Channel-</span>
                    <span className="highlight">IQ</span>
                </h1>

                <nav className="nav">
                    <a href="#clipper">Clipper</a>
                    
                    {/* 🔹 Show User Profile Instead of Sign-in */}
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
                </nav>
            </header>

            <main className="main-content">
                <section className="clipper-section">
                    <button className="clipper-btn" onClick={handleClipperClick}>Clipper</button>

                    <div className="viral-clips">
                        <h3>Your Viral Clips</h3>
                        <div className="clip-thumbnails">
                            {error ? (
                                <p className="error-message">{error}</p>
                            ) : (
                                processedClips.map((clip, index) => (
                                    <div key={index} className="clip-container">
                                        <video
                                            src={clip.url}
                                            controls
                                            className="clip-thumbnail"
                                        />
                                        <label className="clip-checkbox">
                                            <input
                                                type="radio"
                                                name="clipSelection"
                                                onChange={() => handleClipSelection(clip)}
                                                checked={selectedClip && selectedClip.url === clip.url}
                                            />
                                            Select Clip {index + 1}
                                        </label>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="features">
                        <h3>Select Features to Apply:</h3>
                        {["Noise Reduction", "Video Quality", "SEO", "Captions"].map((feature) => (
                            <button
                                key={feature}
                                className={`feature-btn ${selectedFeatures.includes(feature) ? "active" : ""}`}
                                onClick={() => handleFeatureToggle(feature)}
                            >
                                {feature}
                            </button>
                        ))}
                    </div>

                    <div className="optimize-btn">
                        <button
                            onClick={handleOptimize}
                            disabled={!selectedClip || selectedFeatures.length === 0 || loading}
                        >
                            {loading ? "Processing..." : "Optimize"}
                        </button>
                    </div>
                </section>
            </main>
        </div>
    );
}

export default ClipPreview;