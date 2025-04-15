import React, { useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { doc, getDoc } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import Clipper from './clipper'; // Import the Clipper component
import './HomePage.css'; // Ensure your CSS file is imported

const HomePage = () => {
  const { user, logout, login } = useContext(UserContext);
  const navigate = useNavigate();
  const [loadingUser, setLoadingUser] = useState(true);
  const [scrollLocked, setScrollLocked] = useState(true);
  const titleRef = useRef(null);
  const subtitleRef = useRef(null);
  const previewRef = useRef(null);
  const buttonRef = useRef(null);

  // Fetch user from Firestore or localStorage
  useEffect(() => {
    const fetchUserFromFirestore = async () => {
      if (user) {
        setLoadingUser(false);
        return;
      }

      let storedUser = null;
      try {
        storedUser = JSON.parse(localStorage.getItem("user"));
      } catch (e) {
        console.warn("Invalid user data in localStorage");
      }

      if (storedUser?.uid) {
        try {
          const userDoc = await getDoc(doc(db, "users", storedUser.uid));
          if (userDoc.exists()) {
            console.log("User Data from Firestore:", userDoc.data());
            login(userDoc.data());
          }
        } catch (error) {
          console.error("Error fetching user data from Firestore:", error);
        }
      }

      setLoadingUser(false);
    };

    fetchUserFromFirestore();
  }, [user, login]);

  // Animate elements on mount
  useEffect(() => {
    const elements = [titleRef, subtitleRef, previewRef, buttonRef];
    elements.forEach((ref, index) => {
      if (ref.current) {
        setTimeout(() => {
          ref.current.classList.add("animate-in");
        }, index * 200);
      }
    });
  }, []);
  

  // Text animation effect
  useEffect(() => {
    const animateElements = () => {
      const elements = [
        titleRef.current,
        subtitleRef.current,
        previewRef.current,
        buttonRef.current
      ];
      
      elements.forEach((el, index) => {
        if (el) {
          setTimeout(() => {
            el.style.opacity = 1;
            el.style.transform = 'translateY(0)';
          }, index * 200);
        }
      });
    };

    setTimeout(animateElements, 300);
  }, []);
  // Update the useEffect to actually use the scrollLocked value
// Update your scroll lock useEffect hook to this:
useEffect(() => {
  const handleScroll = (e) => {
    if (scrollLocked) {
      e.preventDefault();
      e.stopPropagation();
      window.scrollTo(0, 0);
    }
  };

  if (scrollLocked) {
    window.scrollTo(0, 0);
    // Use { passive: false } to ensure preventDefault works
    window.addEventListener('wheel', handleScroll, { passive: false });
    window.addEventListener('touchmove', handleScroll, { passive: false });
    document.body.classList.add('scroll-lock');
  }

  return () => {
    window.removeEventListener('wheel', handleScroll);
    window.removeEventListener('touchmove', handleScroll);
    document.body.classList.remove('scroll-lock');
  };
}, [scrollLocked]);

  const scrollToClipper = () => {
    setScrollLocked(false);
    const clipperSection = document.querySelector('.clipper-section');
    if (clipperSection) {
      clipperSection.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="home">
      {/* Background Logo */}

      {/* Navbar */}
      {/* Header */}
      <header className="dashboard-header">
  <div className="logo-container" onClick={() => navigate("/")}>
    <h1 className="logo">
      <span className="logo-bold">Channel-</span>
      <span className="logo-highlight">IQ</span>
    </h1>
  </div>

  <div className="header-right">
    <a 
      className="nav-link" 
      href="/terms" // or use navigate("/terms") if you're using React Router
      style={{ marginRight: '1rem', textDecoration: 'none', color: 'var(--color-text)', fontWeight: 500 }}
    >
      Terms & Services
    </a>
    <a 
        className="nav-link" 
        href="/videos" // Add this new link
        style={{ marginRight: '1rem', textDecoration: 'none', color: 'var(--color-text)', fontWeight: 500 }}
    >
        Videos
    </a>

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

      {/* Hero Section */}
      <div className="hero">
        <h1 className="hero__title" ref={titleRef}>
          Your All-in-One AI Tool to Instantly Boost <br />
          <span className="hero__title-highlight">Quality, SEO & YouTube Dominance</span>
        </h1>

        <p className="hero__subtitle" ref={subtitleRef}>
          All-powered editing suite for professional creators
        </p>

        {/* Features Grid */}
        {/* Features Grid */}
<div className="features-grid">
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">✂️</span>
    <span>Smart Clipping</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">📝</span>
    <span>Auto Captions</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">🔇</span>
    <span>Noise Removal</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">🖼️</span>
    <span>4K Upscaling</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">🔍</span>
    <span>SEO Optimization</span>
  </div>
</div>

       {/* Video Preview with enhanced size */}
       <div className="preview" ref={previewRef}>
  <video 
    className="preview__video" 
    autoPlay 
    loop 
    muted 
    playsInline
    onLoadedData={() => console.log("Video loaded successfully")}
    onError={(e) => console.error("Video error:", e.target.error)}
  >
    <source src="/videos/test.mp4" type="video/mp4" />
    <p>Your browser does not support video playback.</p>
  </video>
</div>

        {/* CTA Button */}
        <div className="cta" ref={buttonRef}>
          <button className="cta__button" onClick={scrollToClipper}>
            Get Started
          </button>
          <div className="cta__glow"></div>
        </div>
      </div>

      {/* Clipper Section */}
      <div className="clipper-section">
        <Clipper />
      </div>
    </div>
  );
};

export default HomePage;
