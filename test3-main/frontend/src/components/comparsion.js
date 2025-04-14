import React, { useEffect, useState, useContext } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import "./comparsion.css";
import { UserContext } from "./UserContext";

const Comparison = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext);
  

  const { 
    results, 
    videoURL, 
    selectedFeatures, 
    seoData, 
    localVideoPath,
    s3Key,
    processedS3Url 
  } = location.state || {};
  
  const [originalSeoData, setOriginalSeoData] = useState(null);
  const [error, setError] = useState(null);
  const [videoUrls, setVideoUrls] = useState({
    original: null,
    enhanced: null
  });

  // Helper function to get video URLs
  const getVideoUrls = async () => {
    let originalUrl = null;
    let enhancedUrl = null;

    // Check for S3 URLs first
    if (processedS3Url) {
      enhancedUrl = processedS3Url;
    } else if (results?.audio_processing?.s3_url) {
      enhancedUrl = results.audio_processing.s3_url;
    } else if (results?.video_upscaling?.s3_url) {
      enhancedUrl = results.video_upscaling.s3_url;
    }

    // If no S3 URL, try local paths
    if (!enhancedUrl && localVideoPath) {
      const filename = localVideoPath.split("\\").pop();
      enhancedUrl = `http://127.0.0.1:8000/media/processed/${filename}`;
    }

    // Get original video URL
    if (s3Key) {
      originalUrl = `https://fetchingvideo1.s3.amazonaws.com/${s3Key}`;
    } else if (videoURL) {
      originalUrl = videoURL;
    } else if (localVideoPath) {
      const filename = localVideoPath.split("\\").pop();
      originalUrl = `http://127.0.0.1:8000/media/videos/${filename}`;
    }

    setVideoUrls({
      original: originalUrl,
      enhanced: enhancedUrl
    });
  };

  const fetchOriginalSeo = async () => {
    try {
      const payload = { videoURL };
      const response = await axios.post('http://127.0.0.1:8000/api/fetch-data/', payload, {
        headers: { 'Content-Type': 'application/json' }
      });
      setOriginalSeoData(response.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch original SEO data.');
    }
  };

  useEffect(() => {
    getVideoUrls();
    
    if (selectedFeatures?.includes('SEO')) {
      fetchOriginalSeo();
    }
  }, [location.state]);

  const renderSeoComparison = () => {
    if (!originalSeoData || !seoData) return null;

    return (
      <div className="comparison-grid">
        <div className="comparison-card">
          <h3 className="card-title">Original SEO Metrics</h3>
          <div className="metrics-container">
            <div className="metric-item">
              <h4 className="metric-label">Title</h4>
              <p className="metric-value">{originalSeoData.title || 'No title'}</p>
            </div>
            <div className="metric-item">
              <h4 className="metric-label">Description</h4>
              <p className="metric-value">{originalSeoData.description || 'No description'}</p>
            </div>
            <div className="metric-item">
              <h4 className="metric-label">Tags</h4>
              <p className="metric-value">{originalSeoData.tags?.join(', ') || 'No tags'}</p>
            </div>
          </div>
        </div>
        <div className="comparison-card">
          <h3 className="card-title">Optimized SEO Metrics</h3>
          <div className="metrics-container">
            <div className="metric-item">
              <h4 className="metric-label">Title</h4>
              <p className="metric-value">{seoData.title || 'No title'}</p>
            </div>
            <div className="metric-item">
              <h4 className="metric-label">Description</h4>
              <p className="metric-value">{seoData.description || 'No description'}</p>
            </div>
            <div className="metric-item">
              <h4 className="metric-label">Tags</h4>
              <p className="metric-value">{seoData.tags?.join(', ') || 'No tags'}</p>
            </div>
          </div>
        </div>
      </div>
    );
  };
  const renderVideoComparison = () => {
    if (!videoUrls.original || !videoUrls.enhanced) {
      return <p>No video available for comparison</p>;
    }

    return (
      <div className="comparison-grid">
        <div className="comparison-card">
          <h3 className="card-title">Original</h3>
          {videoUrls.original.includes('youtube.com') ? (
            <iframe 
              width="560" 
              height="315" 
              src={`https://www.youtube.com/embed/${videoUrls.original.split('v=')[1]}`} 
              frameBorder="0" 
              allowFullScreen
            ></iframe>
          ) : (
            <video className="video-player" controls>
              <source src={videoUrls.original} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          )}
        </div>
        <div className="comparison-card">
          <h3 className="card-title">Enhanced</h3>
          <video className="video-player" controls>
            <source src={videoUrls.enhanced} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
      </div>
    );
  };

  return (
    <div className="comparison-app">
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
      
      <div className="comparison-container">
        <h1 className="comparison-title">Video Optimization Results</h1>
        {error && <div className="error-message">{error}</div>}
        {selectedFeatures?.includes('SEO') && renderSeoComparison()}
        {(selectedFeatures?.includes('Noise Reduction') || 
         selectedFeatures?.includes('Video Quality') ||
         selectedFeatures?.includes('Captions')) && renderVideoComparison()}
      </div>
    </div>
  );
};

export default Comparison;