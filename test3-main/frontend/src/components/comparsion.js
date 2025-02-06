import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import "./comparsion.css";

const Comparison = () => {
  const location = useLocation();
  const navigate = useNavigate();  // Added navigation hook
  const { results, videoURL, selectedFeatures, seoData, localVideoPath } = location.state || {};
  console.log(results, videoURL, selectedFeatures, seoData, localVideoPath)
  const [originalSeoData, setOriginalSeoData] = useState(null);
  const [error, setError] = useState(null);

  const getMediaPath = (path) => {
    if (!path) return null;
    const filename = path.split("\\").pop();
    return `http://127.0.0.1:8000/media/videos/${filename}`;
  };
  const getprocessedPath = (path) => {
    if (!path) return null;
    const filename = path.split("\\").pop();
    return `http://127.0.0.1:8000/media/processed/${filename}`;
  };

  const fetchOriginalSeo = async () => {
    try {
      const payload = { videoURL };
      const response = await axios.post('http://127.0.0.1:8000/api/fetch-data/', payload, {
        headers: { 'Content-Type': 'application/json' }
      });
      console.log(response.data.data)
      setOriginalSeoData(response.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch original SEO data.');
    }
  };

  useEffect(() => {
    if (selectedFeatures.includes('SEO')) {
      fetchOriginalSeo();
    }
  }, [videoURL, selectedFeatures]);

  const calculateImprovement = (original, optimized) => {
    const originalLength = original?.length || 0;
    const optimizedLength = optimized?.length || 0;
    if (originalLength === 0) return '0%';
    return `${((optimizedLength - originalLength) / originalLength * 100).toFixed(1)}%`;
  };

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
              <p className="improvement-text">
              </p>
            </div>
            <div className="metric-item">
              <h4 className="metric-label">Description</h4>
              <p className="metric-value">{seoData.description || 'No description'}</p>
              <p className="improvement-text">
              </p>
            </div>
            <div className="metric-item">
              <h4 className="metric-label">Tags</h4>
              <p className="metric-value">{seoData.tags?.join(', ') || 'No tags'}</p>
              <p className="improvement-text">
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderAudioComparison = () => {
    const originalPath = getMediaPath(localVideoPath);
    const enhancedPath = getprocessedPath(results?.audio_processing?.processed_file_path);

    if (!originalPath || !enhancedPath) return null;

    return (
      <div className="comparison-grid">
        <div className="comparison-card">
          <h3 className="card-title">Original</h3>
          <video className="video-player" controls>
            <source src={originalPath} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
        <div className="comparison-card">
          <h3 className="card-title">Enhanced</h3>
          <video className="video-player" controls>
            <source src={enhancedPath} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
      </div>
    );
  };

  const renderVideoQualityComparison = () => {
    const originalPath = getMediaPath(localVideoPath);
    const enhancedPath = getprocessedPath(results?.video_upscaling?.processed_file_path);

    if (!originalPath || !enhancedPath) return null;

    return (
      <div className="comparison-grid">
        <div className="comparison-card">
          <h3 className="card-title">Original</h3>
          <video className="video-player" controls>
            <source src={originalPath} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
        <div className="comparison-card">
          <h3 className="card-title">Enhanced</h3>
          <video className="video-player" controls>
            <source src={enhancedPath} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
      </div>
    );
  };

  return (
    <div className="seo-app">
      <header className="header">
        <h1 className="logo">
          <span className="bold">Channel-</span>
          <span className="highlight">IQ</span>
        </h1>
        <nav className="nav">
          <a>Clipper</a>
          <a>SEO</a>
          <a>Thumbnail</a>
          <a>Pricing</a>
          <button className="sign-in">Sign in</button>
          <button className="sign-up">Sign up</button>
          <button
            className="home-button"
            onClick={() => navigate('/clipper')}
          >
            Home
          </button>
        </nav>
      </header>

      <div className="comparison-container">
        <h1 className="comparison-title">Video Optimization Results</h1>
        {/* Show SEO comparison if selected */}
        {selectedFeatures.includes('SEO') && renderSeoComparison()}
        {/* Prioritize audio processing if selected */}
        {selectedFeatures.includes('Noise Reduction') && renderAudioComparison()}

        {/* Show video quality comparison only if audio processing is not selected */}
        {!selectedFeatures.includes('Noise Reduction') &&
         selectedFeatures.includes('Video Quality') &&
         renderVideoQualityComparison()}
      </div>
    </div>
  );
};

export default Comparison;