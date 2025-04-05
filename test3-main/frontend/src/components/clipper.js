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
function Clipper() {
    const { user, logout } = useContext(UserContext); // Get user details from Context

    const [videoURL, setVideoURL] = useState("");
    const [videoData, setVideoData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [processing, setProcessing] = useState(false); // New state for processing
    const [error, setError] = useState(null);
    const [optimizationType, setOptimizationType] = useState("");
    const [aspectRatio, setAspectRatio] = useState("16:9");
    const [clipLength, setClipLength] = useState("90"); // Separate state for clip length
    const [clipCount, setClipCount] = useState(1);
    const [selectedFeatures, setSelectedFeatures] = useState([]); // New state for feature selection
    const [localVideoPath, setLocalVideoPath] = useState(null);
    const [validationError, setValidationError] = useState("");
    const [videoResolution, setVideoResolution] = useState(null);
    const navigate = useNavigate();
    const saveOriginalVideoToDB = async (videoTitle, s3Url, videoURL, localVideoPath) => {
            if (!user || !user.uid) {
                console.log("❌ User not logged in. Cannot save data.");
                return;
            }
        
            // Validate videoTitle (no special characters or empty)
            if (!videoTitle || /[\/\\\.#$\[\]]/.test(videoTitle)) {
                console.error("❌ Invalid video title");
                return;
            }
        
            try {
                // 🔹 Store metadata under `fetchedVideos` subcollection
                const fetchRef = doc(db, "users", user.uid, "videos", videoTitle, "fetchedVideos", "metadata");
        
                await setDoc(fetchRef, {
                    videoURL,
                    title: videoTitle,
                    originalS3Url: s3Url,
                    localVideoPath,  // ✅ Store local video path as well
                    timestamp: serverTimestamp(),  // Consistent Firestore timestamp
                }, { merge: true });
        
                console.log("✅ Original Video saved under 'fetchedVideos' collection in Firestore.");
            } catch (error) {
                console.error("🔥 Error saving original video to Firestore:", error);
                // Optional: Alert the user here via UI
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
        
            if (!videoURL.trim()) {
                setError("❌ Please enter a valid YouTube URL.");
                setLoading(false);
                return;
            }
        
            // YouTube URL validation using regex
            const isValidYouTubeUrl = /^(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/(watch\?v=|embed\/|v\/)[a-zA-Z0-9_-]+(&[a-zA-Z0-9_=&]*)?$/.test(videoURL);
            if (!isValidYouTubeUrl) {
                setError("❌ Please enter a valid YouTube URL.");
                setLoading(false);
                return;
            }
        
            try {
                // Step 1: Fetch video metadata
                let data;
                try {
                    data = await fetchVideoMetadata(videoURL);
                } catch (err) {
                    setError("❌ Failed to fetch video metadata.");
                    setLoading(false);
                    return;
                }
                setVideoData(data);
        
                // Step 2: Download & Upload Video to S3
                const downloadResponse = await downloadAndUploadVideo(videoURL);
                if (!downloadResponse || !downloadResponse.url || !downloadResponse.local_path) {
                    console.error("🚨 Missing S3 URL or local path in response", downloadResponse);
                    setError("❌ Failed to download and upload video.");
                    setLoading(false);
                    return;
                }
        
                const s3Url = downloadResponse.url;
                const localPath = downloadResponse.local_path; // Store locally
                console.log("🔍 S3 URL before storing:", s3Url);
                console.log("📁 Local Video Path:", localPath);
        
                // Step 3: Store Video Details in Firestore
                if (user && user.uid) {
                    await saveOriginalVideoToDB(data.title, s3Url, videoURL, localPath);
                } else {
                    setError("❌ Please log in to save the video.");
                    setLoading(false);
                    return;
                }
        
                setLocalVideoPath(localPath);
        
                // Step 4: Check Video Resolution (Optional)
                try {
                    const resolutionResponse = await axios.post(
                        "http://127.0.0.1:8000/api/check-resolution/",
                        { video_path: localPath },
                        { headers: { "Content-Type": "application/json" } }
                    );
                    if (resolutionResponse.data.resolution) {
                        setVideoResolution(resolutionResponse.data.resolution);
                    }
                } catch (resError) {
                    console.error("⚠️ Resolution Check Error:", resError);
                    setError("❌ Failed to check video resolution.");
                }
            } catch (err) {
                console.error("❌ Fetch Error:", err);
                setError(err.response?.data?.error || err.message || "❌ Failed to process video.");
            } finally {
                setLoading(false);
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
        // Check if video data exists
        if (!videoData) {
            alert("Please fetch a video first before generating.");
            return;
        }

        // Check if optimization type is selected
        if (!optimizationType) {
            alert("Please select an optimization type (Long Form or Short Form).");
            return;
        }

        // For Long Form, check if at least one feature is selected
        if (optimizationType === "Long Form" && selectedFeatures.length === 0) {
            alert("Please select at least one feature for Long Form optimization.");
            return;
        }
        if (optimizationType === "Short Form") {
            if (!clipLength || !clipCount) {
                alert("Please select clip length and number of clips for Short Form optimization.");
                return;
            }
        }

        // Check user authentication (added from first code)
        if (!user || !user.uid) {
            console.error("❌ User is not authenticated.");
            alert("❌ Please login before optimizing videos.");
            return;
        }

        const userId = user.uid;
        const videoId = uuidv4();
        let sanitizedTitle = videoData.title.replace(/[^\w\s]/gi, " ").trim() || `video_${Date.now()}`;

        // Handle Long Form with SEO separately
        if (optimizationType === "Long Form" && selectedFeatures.includes("SEO")) {
            // Run the `seo.py` script and navigate to the SEO page
            setProcessing(true);
            try {
                console.log("Running SEO script...");

                // Call the backend to execute the `seo.py` script
                const response = await axios.post(
                    "http://127.0.0.1:8000/api/seo/",
                    {
                        videoURL,            // Pass the video URL
                        selectedFeatures,
                        localVideoPath,
                        userId, // Use the extracted userId
                        videoId  // Include the videoId
                    },
                    {
                        headers: {
                            "Content-Type": "application/json",
                        },
                    }
                );

                console.log("Response:", response.data);

                // Firebase storage logic (added from first code)
                const processedURL = response.data.results?.s3_upload?.url || null;
                const thumbnail = response.data.results?.thumbnail || null;

                // Save data to Firestore
                let saveData = {
                    userId,
                    videoId,
                    selectedFeatures,
                    status: response?.status === 200 ? "Success" : "Processing",
                    timestamp: serverTimestamp(),
                    seo: response.data.results?.seo || {}
                };

                // If SEO + Other Features, add optimized_vid data
                if (selectedFeatures.length > 1) {
                    saveData.optimized_vid = {
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

                // Save to Firestore
                await setDoc(
                    doc(db, `users/${userId}/videos/${sanitizedTitle}/generate/LongForm`),
                    saveData,
                    { merge: true }
                );

                console.log(`✅ Data saved under videoTitle: ${sanitizedTitle}`);

                // Determine display media for SEO
                const displayMedia = selectedFeatures.length === 1 ? thumbnail : 
                    (response.data.results?.clips?.length > 0 ? response.data.results.clips[0] : null);

                // Navigate to the SEO page and pass the SEO data
                navigate("/Seo", {
                    state: {
                        message: response.data.message,
                        results: response.data.results,
                        videoURL,
                        localVideoPath,
                        selectedFeatures,
                        videoTitle: videoData.title,
                        displayMedia
                    },
                });

            } catch (err) {
                console.error("Error generating SEO data:", err);
                alert(err.response?.data?.error || "Error during SEO processing. Please try again.");
            } finally {
                setProcessing(false);
            }
            return; // Exit from the function to avoid further processing
        }

        // Handle Long Form without SEO
        if (optimizationType === "Long Form" && !selectedFeatures.includes("SEO")) {
            // Process the features for optimization
            setProcessing(true);
            try {
                console.log("Running video optimization...");
                console.log("Local Video Path:", localVideoPath);
                const payload = {
                    videoURL,
                    optimizationType,
                    aspectRatio,
                    selectedFeatures,
                    localVideoPath,
                    userId,
                    videoId
                };
                const csrfToken = document.cookie
                    .split("; ")
                    .find((row) => row.startsWith("csrftoken"))
                    ?.split("=")[1];
        
                const response = await axios.post(
                    "http://127.0.0.1:8000/api/seo/",
                    payload,
                    {
                        headers: {
                            "X-CSRFToken": csrfToken,
                            "Content-Type": "application/json",
                        },
                    }
                );
        
                alert(response.data.message || "Video optimization started!");
                console.log("Response Data:", response.data);
                
                // Firebase storage logic (added from first code)
                const processedURL = response.data.results?.s3_upload?.url || null;

                // Save data to Firestore
                await setDoc(
                    doc(db, `users/${userId}/videos/${sanitizedTitle}/generate/LongForm`),
                    {
                        userId,
                        videoId,
                        selectedFeatures,
                        status: response?.status === 200 ? "Success" : "Processing",
                        timestamp: serverTimestamp(),
                        optimized_vid: {
                            originalVideoURL: videoURL,
                            processedVideoURL: processedURL,
                            s3FinalURL: processedURL,
                            s3Key: response.data.results?.s3_upload?.key || null,
                            localPath: localVideoPath || null,
                            enhancementType: response.data.results?.enhancementType || "Unknown",
                            status: response.data.results?.s3_upload?.status || "Processing",
                            message: response.data.message || "",
                        }
                    },
                    { merge: true }
                );

                console.log(`✅ Data saved under videoTitle: ${sanitizedTitle}`);
                
                // Navigate to the Optimize Video page and pass the URL and selected features
                navigate("/optimizevideo", {
                    state: {
                        videoURL,
                        results: response.data.results,
                        localVideoPath,
                        selectedFeatures,
                        userId,
                        videoTitle: videoData.title
                    },
                });
            } catch (err) {
                console.error("Error optimizing video:", err);
                alert(err.response?.data?.error || "Error during video optimization. Please try again.");
            } finally {
                setProcessing(false);
            }
            return; // Exit to avoid conflicting redirects
        }

        // Handle Short Form generation
        if (optimizationType === "Short Form") {
            const payload = {
                videoURL,
                optimizationType,
                aspectRatio,
                clipLength,
                clipCount,
                features: selectedFeatures,
                userId,
                videoId
            };
        
            setProcessing(true);
        
            try {
                console.log("Payload:", payload);
                const csrfToken = document.cookie
                    .split("; ")
                    .find((row) => row.startsWith("csrftoken"))
                    ?.split("=")[1];
        
                const response = await axios.post(
                    "http://127.0.0.1:8000/api/process_short_form_video/",
                    payload,
                    {
                        headers: {
                            "X-CSRFToken": csrfToken,
                            "Content-Type": "application/json",
                        },
                    }
                );
                console.log(response);
        
                alert(response.data.message || "Video generation started!");

                // Firebase storage logic (added from first code)
                await setDoc(
                    doc(db, `users/${userId}/videos/${sanitizedTitle}/generate/ShortForm`),
                    {
                        clipLength,
                        clipCount,
                        clips: response.data.clips || [],
                        status: "Processing",
                        timestamp: serverTimestamp(),
                        videoTitle: videoData.title,
                        videoId,
                    },
                    { merge: true }
                );

                console.log(`✅ Short Form saved under videoTitle: ${sanitizedTitle}`);
                
                // Navigate to ClipPreview and pass the clip paths (now S3 URLs)
                navigate("/clippreview", {
                    state: {
                        clipPaths: response.data.clips, // This now contains S3 URL objects
                        videoURL,
                        videoTitle: videoData.title, // Added from first code
                    },
                });
            } catch (err) {
                console.error("Error generating video:", err);
                alert(err.response?.data?.error || "Error during video generation. Please try again.");
            } finally {
                setProcessing(false);
            }
            return; // Exit to avoid displaying a message for long form
        }

        // If neither "Long Form" nor "Short Form" is selected
        alert("Please select either Long Form or Short Form to proceed.");
    };

    return (
        <div className="clipper-wrapper">
            <div className="clipper-container">
                {/* Top nav with Channel-IQ and user info */}
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
                    </nav>
                </header>

                {/* YouTube Video Clipper title */}
                <div className="app-title">
                    <h1>YouTube Video Clipper</h1>
                </div>

                <div className="url-input-container">
                    <input
                        type="text"
                        placeholder="Enter YouTube URL"
                        value={videoURL}
                        onChange={(e) => setVideoURL(e.target.value)}
                        className="url-input"
                        disabled={processing}
                    />
                    <button
                        onClick={handleFetch}
                        disabled={loading || processing}
                        className="fetch-btn"
                    >
                        {loading ? "Fetching..." : "Fetch Video"}
                    </button>
                </div>

                <div className="main-content-grid">
                    {/* Left Column */}
                    <div className="video-preview-container">
                        {videoData && (
                            <div>
                                <div className="video-title-container">
                                    <h3 className="video-section-heading">Title:</h3>
                                    <h2 className="video-title">{videoData.title}</h2>
                                </div>
                                <div className="video-thumbnail-container">
                                    <h3 className="video-section-heading">Thumbnail:</h3>
                                    <img
                                        src={videoData.thumbnail}
                                        alt="Video Thumbnail"
                                        className="video-thumbnail"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right Column */}
                    <div className="settings-container">
                        <div className="optimization-type">
                            <h3>Choose Optimization Type:</h3>
                            <div className="optimization-buttons">
                                <button
                                    className={optimizationType === "Long Form" ? "active" : ""}
                                    onClick={() => handleOptimizationTypeChange("Long Form")}
                                >
                                    Long Form
                                </button>
                                <button
                                    className={optimizationType === "Short Form" ? "active" : ""}
                                    onClick={() => handleOptimizationTypeChange("Short Form")}
                                >
                                    Short Form
                                </button>
                            </div>
                        </div>

                        {optimizationType === "Long Form" && (
                            <div className="features">
                                {["Noise Reduction", "Video Quality", "SEO"].map((feature) => (
                                    <button
                                        key={feature}
                                        className={selectedFeatures.includes(feature) ? "feature-btn active" : "feature-btn"}
                                        onClick={() => handleFeatureToggle(feature)}
                                    >
                                        {feature}
                                    </button>
                                ))}
                            </div>
                        )}

                        {optimizationType === "Short Form" && (
                            <div className="short-form-options">
                                <div className="dropdown-container">
                                    <label htmlFor="clipLength">Clip Length:</label>
                                    <select
                                        id="clipLength"
                                        value={clipLength}
                                        onChange={(e) => setClipLength(e.target.value)}
                                    >
                                        <option value="30">30</option>
                                        <option value="60">60</option>
                                        <option value="90">90</option>
                                        <option value="Auto">Auto</option>
                                    </select>
                                </div>
                                <div className="clip-count-container">
                                    <label htmlFor="clipCount">Number of Clips (1-3):</label>
                                    <input
                                        type="number"
                                        id="clipCount"
                                        value={clipCount}
                                        onChange={(e) => setClipCount(Math.min(Math.max(e.target.value, 1), 3))}
                                        min="1"
                                        max="5"
                                    />
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {error && <p className="error-message">{error}</p>}

                {processing && <p className="processing-message">Processing your video. Please wait...</p>}

                <div className="generate-btn">
                    <button onClick={handleGenerateClick} disabled={processing}>
                        {processing ? "Processing..." : "Generate"}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default Clipper;