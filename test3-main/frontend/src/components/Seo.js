import React, { useState, useEffect, useContext } from "react";
import "./Seo.css";
import { useLocation, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFileLines, faClosedCaptioning, faSearch, faImage } from "@fortawesome/free-solid-svg-icons";
import { fetchVideoMetadata } from "../axios-use/api";
import { UserContext } from "./UserContext"; // Import User Context

function SEO({ videoThumbnail }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Access User Context

  const { message, results, videoURL, localVideoPath, selectedFeatures } = location.state || {};
  console.log(results);

  const [seoMessage, setSeoMessage] = useState(message || "No SEO data received.");
  const [displayVideo, setDisplayVideo] = useState(null);
  const [thumbnail, setThumbnail] = useState(videoThumbnail || "https://via.placeholder.com/300x300");

  const seoData = results?.seo || {};
  const keywords = seoData.keywords?.length ? seoData.keywords.join(", ") : "No keywords available.";
  const description = seoData.description || "No description available.";
  const title = seoData.title || "No title available.";
  const tags = seoData.tags?.length ? seoData.tags.join(", ") : "No tags available.";

  useEffect(() => {
    const fetchMedia = async () => {
      console.log("Results:", results);
      console.log("selectedFeatures:", selectedFeatures);
      try {
        if (results?.audio_processing?.enhanced_video_path) {
          const filename = results.audio_processing.enhanced_video_path.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/${filename}`);
          console.log("Using audio-enhanced video:", filename);
        } else if (results?.video_upscaling?.processed_file_path) {
          const filename = results.video_upscaling.processed_file_path.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/${filename}`);
          console.log("Using upscaled video:", filename);
        } else {
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
  }, [results, videoURL]);

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
                <p>{description}</p>
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

            {/* Add Compare Results Button */}
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
          </div>
        </div>
      </main>
    </div>
  );
}

export default SEO;
