import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import "./comparsion.css";

const Comparison = () => {
  const location = useLocation();
  const navigate = useNavigate();
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

  // Remove the separate getprocessedPath function since it's now handled in getMediaPath

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

  // Since getMediaPath is now async, we need to modify the rendering functions
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
        {selectedFeatures.includes('SEO') && renderSeoComparison()}
        {(selectedFeatures.includes('Noise Reduction') || 
          selectedFeatures.includes('Video Quality')) && 
          renderVideoComparison()}
      </div>
    </div>
  );
};

export default Comparison;