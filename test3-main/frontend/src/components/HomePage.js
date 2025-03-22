import React, { useContext, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "./HomePage.css";
import homepageImage from "./homepage.png";
import { UserContext } from "./UserContext"; // Import global User Context

const HomePage = () => {
  const { user, logout } = useContext(UserContext); // Access global user state
  const navigate = useNavigate();
  
  // Refs for animation elements
  const titleRef = useRef(null);
  const subtitleRef = useRef(null);
  const previewRef = useRef(null);
  const buttonRef = useRef(null);

  // Add animation when component mounts
  useEffect(() => {
    const elements = [titleRef, subtitleRef, previewRef, buttonRef];
    console.log(localStorage.getItem("user")); 
    
    elements.forEach((ref, index) => {
      if (ref.current) {
        // Add animation with staggered delay
        setTimeout(() => {
          ref.current.classList.add('animate-in');
        }, index * 200); // Stagger animations by 200ms
      }
    });
  }, []);

  return (
    <div className="home">
      {/* Navbar */}
      <header className="header">
        <div className="header__logo" onClick={() => navigate("/")}>
          Channel-<span className="header__logo-highlight">IQ</span>
        </div>

        {/* Show user profile if logged in, otherwise show login button */}
        {user ? (
          <div className="user">
            {user.picture && (
              <img src={user.picture} alt="User" className="user__avatar" />
            )}
            <span className="user__name">{user.name}</span>
            <button className="user__logout-btn" onClick={logout}>
              Logout
            </button>
          </div>
        ) : (
          <button 
            className="user__login-btn" 
            onClick={() => navigate("/login")}
          >
            Login
          </button>
        )}
      </header>

      {/* Hero Section */}
      <main className="hero">
        <h1 className="hero__title" ref={titleRef}>
          Clip your long video in <span className="hero__title-highlight">one</span>{" "}
          <span className="hero__title-click">click.</span>
        </h1>

        <p className="hero__subtitle" ref={subtitleRef}>
          <span className="hero__sparkle">✨</span> Meet Clipper, a multi-modal AI that can clip any type of video.
        </p>

        {/* Image Preview Section with enhanced animations */}
        <div className="preview" ref={previewRef}>
          <div className="preview__shadow"></div>
          <img
            src={homepageImage}
            alt="Video clipping preview"
            className="preview__image"
          />

        </div>

        {/* "Get Clips" Button */}
        <div className="cta" ref={buttonRef}>
          <button 
            className="cta__button" 
            onClick={() => navigate("/clipper")}
          >
            Get Clips
          </button>
          <div className="cta__glow"></div>
        </div>
      </main>
    </div>
  );
};

export default HomePage;