// src/components/YouTubeAuthCallback.js
import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';

const YouTubeAuthCallback = () => {
  const [status, setStatus] = useState('Processing...');
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      // Get the authorization code from URL
      const urlParams = new URLSearchParams(location.search);
      const code = urlParams.get('code');
      
      if (code) {
        try {
          // Exchange the code for tokens
          await axios.post('/api/youtube/callback/', { code });
          
          setStatus('YouTube authorization successful!');
          
          // Check if there was a pending upload
          const pendingUpload = localStorage.getItem('pendingUpload');
          if (pendingUpload) {
            localStorage.removeItem('pendingUpload');
            // Redirect back to the upload page
            setTimeout(() => navigate('/optimizevideo'), 1500);
          } else {
            // Redirect to home page
            setTimeout(() => navigate('/home'), 1500);
          }
        } catch (error) {
          console.error('Error in YouTube auth callback:', error);
          setStatus('Authorization failed. Please try again.');
          
          // Redirect back to home page
          setTimeout(() => navigate('/home'), 3000);
        }
      } else {
        setStatus('No authorization code found. Please try again.');
        setTimeout(() => navigate('/home'), 3000);
      }
    };

    handleCallback();
  }, [location, navigate]);

  return (
    <div className="auth-callback-container">
      <h2>YouTube Authorization</h2>
      <div className="auth-status">
        <p>{status}</p>
        {status.includes('successful') && (
          <div className="loader">Redirecting...</div>
        )}
      </div>
    </div>
  );
};

export default YouTubeAuthCallback;