import React, { useEffect, useState, useContext } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import "./comparsion.css";
import { UserContext } from "./UserContext"; // Import User Context

const Comparison = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Access User Context

  const { results, videoURL, selectedFeatures, seoData, localVideoPath } = location.state || {};
  const [originalSeoData, setOriginalSeoData] = useState(null);
  const [error, setError] = useState(null);

  const getMediaPath = async (path) => {
    if (!path) return null;
    const filename = path.split("\\").pop();

    // Try media/videos first
    const mediaUrl = `http://127.0.0.1:8000/media/videos/${filename}`;
    try {
      const mediaResponse = await fetch(mediaUrl, { method: 'HEAD' });
      if (mediaResponse.ok) {
        return mediaUrl;
      }
    } catch (error) {
      console.log('File not found in media/videos');
    }

    // If not found, try media/processed
    const processedUrl = `http://127.0.0.1:8000/media/processed/${filename}`;
    try {
      const processedResponse = await fetch(processedUrl, { method: 'HEAD' });
      if (processedResponse.ok) {
        return processedUrl;
      }
    } catch (error) {
      console.log('File not found in media/processed');
    }

    return null; // Return null if file not found in either location
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

  const [videoUrls, setVideoUrls] = useState({
    original: null,
    enhanced: null
  });

  useEffect(() => {
    const loadVideoPaths = async () => {
      if (localVideoPath) {
        const originalUrl = await getMediaPath(localVideoPath);
        let enhancedUrl = null;

        if (results?.audio_processing?.processed_file_path) {
          enhancedUrl = await getMediaPath(results.audio_processing.processed_file_path);
        } else if (results?.video_upscaling?.processed_file_path) {
          enhancedUrl = await getMediaPath(results.video_upscaling.processed_file_path);
        }

        setVideoUrls({
          original: originalUrl,
          enhanced: enhancedUrl
        });
      }
    };

    loadVideoPaths();
  }, [localVideoPath, results]);

  useEffect(() => {
    if (selectedFeatures.includes('SEO')) {
      fetchOriginalSeo();
    }
  }, [videoURL, selectedFeatures]);

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
    if (!videoUrls.original || !videoUrls.enhanced) return null;

    return (
      <div className="comparison-grid">
        <div className="comparison-card">
          <h3 className="card-title">Original</h3>
          <video className="video-player" controls>
            <source src={videoUrls.original} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
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

      <div className="comparison-container">
        <h1 className="comparison-title">Video Optimization Results</h1>
        {selectedFeatures.includes('SEO') && renderSeoComparison()}
        {(selectedFeatures.includes('Noise Reduction') || selectedFeatures.includes('Video Quality')) && renderVideoComparison()}
      </div>
    </div>
  );
};

export default Comparison;
