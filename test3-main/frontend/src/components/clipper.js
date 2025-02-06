import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { fetchVideoMetadata, downloadAndUploadVideo } from "../axios-use/api";
import "./clipper.css";

function Clipper() {
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

const handleFetch = async () => {
    setLoading(true);
    setError(null);
    setVideoData(null);
    setVideoResolution(null);

    if (!videoURL.trim()) {
        setError("Please enter a valid YouTube URL.");
        setLoading(false);
        return;
    }

    try {
        // Fetch video metadata
        const data = await fetchVideoMetadata(videoURL);
        setVideoData(data);

        // Download video and get local path
        const downloadResponse = await downloadAndUploadVideo(videoURL);
        console.log("Download response:", downloadResponse);

        if (!downloadResponse.local_path) {
            throw new Error("No local path received from video download");
        }

        // Store the local path
        const videoPath = downloadResponse.local_path;
        setLocalVideoPath(videoPath);

        // Check video resolution
        try {
            console.log("Sending video path for resolution check:", videoPath);

            const resolutionResponse = await axios.post(
                "http://127.0.0.1:8000/api/check-resolution/",
                {
                    video_path: videoPath
                },
                {
                    headers: {
                        'Content-Type': 'application/json',
                    }
                }
            );

            console.log("Resolution response:", resolutionResponse.data);

            if (resolutionResponse.data.resolution) {
                setVideoResolution(resolutionResponse.data.resolution);

                // Inform user if video is above 480p

            }
        } catch (resError) {
            console.error("Resolution check error:", resError);
            console.error("Resolution check error details:", resError.response?.data);
            setError("Failed to check video resolution. Some features may be limited.");
        }

    } catch (err) {
        console.error("Error during fetch:", err);
        setError(err.response?.data?.error || err.message || "Failed to process video. Please try again.");
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
                    localVideoPath// Include selected features
                },
                {
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );

            console.log("Response:",response.data);

            // Navigate to the SEO page and pass the SEO data
            navigate("/Seo", {
                state: {
                    message: response.data.message,
                    results: response.data.results,
                    videoURL,
                    localVideoPath,
                    selectedFeatures
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
            console.log("Local Video Path:", localVideoPath)
            const payload = {
                videoURL,
                optimizationType,
                aspectRatio,
                selectedFeatures,
                 localVideoPath,
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
            console.log("Response Data:",response.data)
            // Navigate to the Optimize Video page and pass the URL and selected features
            navigate("/optimizevideo", {
                state: {
                    videoURL,
                    results: response.data.results
                    ,localVideoPath,
                    selectedFeatures
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
            clipLength, // Keep clipLength separate
            clipCount,
            features: selectedFeatures, // Include selected features in the payload
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
            console.log(response)

            alert(response.data.message || "Video generation started!");
            // Navigate to ClipPreview and pass the clip paths
            navigate("/clippreview", {
                state: {
                    clipPaths: response.data.clips,
                    videoURL,
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
        <div className="clipper-container">
            <header className="header">
                <h1 className="logo">
                    <span className="bold">Channel-</span>
                    <span className="highlight">IQ</span>
                </h1>
                <nav className="nav">
                    <a href="#clipper">Clipper</a>
                    <a href="#pricing">Pricing</a>
                    <button className="sign-in">Sign in</button>
                    <button className="sign-up">Sign up</button>
                </nav>
            </header>

            <h1>YouTube Video Clipper</h1>

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

            {error && <p className="error-message">{error}</p>}

            {videoData && (
                <div className="video-preview-container">
                    <h2>{videoData.title}</h2>
                    <img
                        src={videoData.thumbnail}
                        alt="Video Thumbnail"
                        className="video-thumbnail"
                    />
                </div>
            )}

            <div className="optimization-type">
                <h3>Choose Optimization Type:</h3>
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

            {processing && <p className="processing-message">Processing your video. Please wait...</p>}

            <div className="generate-btn">
                <button onClick={handleGenerateClick}>
                    {processing ? "Processing..." : "Generate"}
                </button>
            </div>
        </div>
    );
}

export default Clipper;