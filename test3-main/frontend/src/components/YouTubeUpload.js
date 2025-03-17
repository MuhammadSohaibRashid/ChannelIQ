import React, { useContext, useEffect, useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { useNavigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";
import axios from "axios";

import { UserContext } from "./UserContext";
import "./LoginPage.css";
import "./base.css";

const LoginPage = () => {
  const navigate = useNavigate();
  const { user, login, logout } = useContext(UserContext);
  const [authStatus, setAuthStatus] = useState({
    google: false,
    youtube: false,
  });

  // Check if user is already logged in & navigate to home
  useEffect(() => {
    if (user) {
      navigate("/home");
      // Check YouTube authorization status
      checkYouTubeAuth();
    }
  }, [user, navigate]);

  // Check YouTube auth status when user logs in
  const checkYouTubeAuth = async () => {
    try {
      const response = await axios.get('/api/youtube/check-auth/', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('authToken')}`
        }
      });
      
      setAuthStatus(prev => ({
        ...prev,
        youtube: response.data.is_authorized
      }));
    } catch (error) {
      console.error('Error checking YouTube auth:', error);
      setAuthStatus(prev => ({
        ...prev,
        youtube: false
      }));
    }
  };

  // Handle Google Login Success
  const handleGoogleLoginSuccess = async (response) => {
    try {
      const decodedUser = jwtDecode(response.credential); // Decode the token
      console.log("Google Login Success:", decodedUser);
      
      // Get authentication token from backend
      const authResponse = await axios.post('/api/auth/google-login/', {
        token: response.credential
      });
      
      // Store auth token
      localStorage.setItem('authToken', authResponse.data.token);
      
      // Save user in context & localStorage
      login({
        ...decodedUser,
        token: authResponse.data.token
      });
      
      setAuthStatus(prev => ({
        ...prev,
        google: true
      }));
      
      // Check YouTube authorization
      await checkYouTubeAuth();
      
      // Redirect to Home Page
      navigate("/home");
    } catch (error) {
      console.error("Error processing Google login:", error);
    }
  };

  // Handle Google Login Failure
  const handleGoogleLoginFailure = () => {
    console.log("Google Login Failed");
  };

  // Handle YouTube Authorization
  const handleYouTubeAuth = () => {
    // Store current page so we can return after auth
    localStorage.setItem('authRedirect', '/home');
    
    // Redirect to Django backend auth endpoint
    window.location.href = '/api/youtube/authorize/';
  };

  return (
    <div className="login-page">
      <header className="header">
        <h1 className="logo">
          <span className="bold">Channel-</span>
          <span className="highlight">IQ</span>
        </h1>
        <nav className="nav">
          {user && (
            <button className="sign-out" onClick={logout}>
              Logout
            </button>
          )}
        </nav>
      </header>

      <div className="login-container">
        <div className="left-panel">
          <h1>
            Channel-<span className="highlight">IQ</span>
          </h1>
          <p>
            Turn your long videos into <span className="highlight">VIRAL</span> short clips.
          </p>
          <ul>
            <li>✔ AI SEO</li>
            <li>✔ Auto Caption</li>
            <li>✔ Auto Clipping</li>
            <li>✔ Quality Enhancer</li>
            <li>✔ Sound Improvement</li>
            <li>✔ YouTube Upload</li>
          </ul>
        </div>

        <div className="right-panel">
          <h2>{user ? `Welcome, ${user.name}` : "Login to your account"}</h2>

          {user ? (
            <div className="auth-status">
              <div className="auth-item">
                <span className="auth-label">Google Account:</span>
                <span className="auth-value connected">Connected</span>
              </div>
              
              <div className="auth-item">
                <span className="auth-label">YouTube Account:</span>
                {authStatus.youtube ? (
                  <span className="auth-value connected">Connected</span>
                ) : (
                  <>
                    <span className="auth-value not-connected">Not Connected</span>
                    <button 
                      className="connect-btn youtube-btn" 
                      onClick={handleYouTubeAuth}
                    >
                      Connect YouTube
                    </button>
                  </>
                )}
              </div>
              
              <div className="user-actions">
                <button className="continue-btn" onClick={() => navigate('/home')}>
                  Continue to Dashboard
                </button>
                <button className="logout-btn" onClick={logout}>
                  Logout
                </button>
              </div>
            </div>
          ) : (
            <div className="login-options">
              <p>Sign in with your Google account to get started:</p>
              <GoogleLogin
                onSuccess={handleGoogleLoginSuccess}
                onError={handleGoogleLoginFailure}
                text="signin_with"
                shape="rectangular"
                theme="filled_blue"
                size="large"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;