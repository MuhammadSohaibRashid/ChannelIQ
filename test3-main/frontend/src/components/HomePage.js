// src/components/HomePage.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './HomePage.css';
import homepageImage from './homepage.png';

const HomePage = ({ setVideoUrl }) => {
  const [url, setUrl] = useState('');
  const navigate = useNavigate();

  const handleGetClips = () => {
    setVideoUrl(url);
    navigate('/clipper'); // Navigate to the Clipper page
  };

  const handleSignup = () => {
    navigate('/login'); // Redirects to the home page
};

  return (
    <div className="home-container">
      <nav className="navbar">
        <div className="logo">Channel-<span className="highlight">IQ</span></div>
        <div className="nav-links">
          <a href="#">Clipper</a>
          <a href="#">SEO</a>
          <a href="#">Thumbnail</a>
          <a href="#">Pricing</a>
          <button className="sign-in-btn" onClick={handleSignup}>Sign In</button>
        </div>
      </nav>
      <main className="main-content">
        <h1>Clip your long video in <span className="highlight">one</span> <span className="regular-text">click</span>.</h1>
        <p>✨ Meet Clipper, multi-modal AI that can clip any type of video.</p>
        <div className="video-preview">
          <img src={homepageImage} alt="Video preview" />
        </div>
        <div className="input-section">
          <input 
            type="url" 
            placeholder="https://www.youtube.com" 
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button className="get-clips-btn" onClick={handleGetClips}>Get Clips</button>
        </div>
      </main>
    </div>
  );
};

export default HomePage;
