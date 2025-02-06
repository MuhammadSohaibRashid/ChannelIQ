import React, { useState } from "react";
import "./Seo_shortform.css";
import { useLocation, useNavigate } from "react-router-dom";

function Seo_shortform({ videoThumbnail }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { message, results, selectedFeatures, selectedClip } = location.state || {};
  const [seoMessage, setSeoMessage] = useState(message || "No SEO data received.");

  const getVideoUrl = () => {
    if (selectedFeatures.length === 1 && selectedFeatures.includes('SEO')) {
      return selectedClip;
    }

    if (results?.audio_processing?.processed_file_path) {
      const fileName = results.audio_processing.processed_file_path.split('\\').pop();
      return `http://127.0.0.1:8000/media/processed/${fileName}`;
    }

    if (results?.video_upscaling?.processed_file_path) {
      const fileName = results.video_upscaling.processed_file_path.split('\\').pop();
      return `http://127.0.0.1:8000/media/processed/${fileName}`;
    }

    return selectedClip;
  };

  const handleCompare = () => {
    const localPath = selectedClip.replace(
      'http://127.0.0.1:8000/media/processed/',
      'C:\\Users\\aqiba\\Desktop\\test3-main\\test3-main\\backend\\media\\processed\\'
    );

    let processedResult = {};
    if (selectedFeatures.includes('Noise Reduction') && results.audio_processing) {
      processedResult = { audio_processing: results.audio_processing };
    } else if (selectedFeatures.includes('Video Quality') && results.video_upscaling) {
      processedResult = { video_upscaling: results.video_upscaling };
    }

    navigate('/comparison', {
      state: {
        results: processedResult,
        selectedFeatures,
        videoURL: null,
        localVideoPath: localPath,
        seoData: null
      }
    });
  };

  return (
    <div className="seo-app">
      <header className="header">
        <h1 className="logo">
          <span className="bold">Channel-</span>
          <span className="highlight">IQ</span>
        </h1>
        <nav className="nav">
          <a href="#clipper">Clipper</a>
          <a href="#seo">SEO</a>
          <a href="#thumbnail">Thumbnail</a>
          <a href="#pricing">Pricing</a>
          <button className="sign-in">Sign in</button>
          <button className="sign-up">Sign up</button>
          <button className="home-button" onClick={() => navigate('/clipper')}>
            Home
          </button>
        </nav>
      </header>

      <main className="main-content">
        <button className="clipper-btn" onClick={() => navigate('/clipper')}>
          Go to Clipper
        </button>

        <div className="clip-section">
          <div className="media-preview">
            <video className="preview-video" controls>
              <source src={getVideoUrl()} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>

          <div className="customize-clip">
            <div className="seo-data">
              <div className="seo-box">
                <h2>Title</h2>
                <p>{results?.seo?.title || "No title available."}</p>
              </div>
              <div className="seo-box">
                <h2>Description</h2>
                <p>{results?.seo?.description || "No description available."}</p>
              </div>
              <div className="seo-box">
                <h2>Keywords</h2>
                <p>{results?.seo?.keywords?.join(", ") || "No keywords available."}</p>
              </div>
              <div className="seo-box">
                <h2>Tags</h2>
                <p>{results?.seo?.tags?.join(", ") || "No tags available."}</p>
              </div>
            </div>
            {(selectedFeatures?.includes('Noise Reduction') || selectedFeatures?.includes('Video Quality')) && (
              <button className="comparison-btn" onClick={handleCompare}>
                Compare Results
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default Seo_shortform;