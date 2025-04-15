import React, { useEffect, useState, useContext } from "react";
import { collection, getDocs, query, orderBy } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import VideoDetails from "./videoDetails";
import { useNavigate } from "react-router-dom";
import "./videoDashboard.css";

const AllVideosPage = () => {
    const { user, logout, login } = useContext(UserContext);
    const navigate = useNavigate();
    const [videos, setVideos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedVideo, setSelectedVideo] = useState(null);
    const [showModal, setShowModal] = useState(false);
    
    useEffect(() => {
        const fetchAllVideos = async () => {
            if (!user || !user.uid) {
                setLoading(false);
                return;
            }
            
            setLoading(true);
            try {
                const videosCollectionRef = collection(db, "users", user.uid, "videos");
                const videosQuery = query(
                    videosCollectionRef,
                    orderBy("timestamp", "desc") // Show newest first
                );
                
                const videoFoldersSnapshot = await getDocs(videosQuery);
                
                const videoPromises = videoFoldersSnapshot.docs.map(async (videoFolder) => {
                    const videoTitle = videoFolder.id;
                    const videoData = videoFolder.data();
                    
                    return {
                        id: videoTitle,
                        videoTitle: videoTitle,
                        title: videoData.title || videoTitle,
                        thumbnailUrl: videoData.thumbnailUrl || "/images/fallback-thumbnail.jpg",
                        timestamp: videoData.timestamp,
                        originalS3Url: videoData.originalS3Url,
                        videoURL: videoData.videoURL
                    };
                });
                
                const videoList = await Promise.all(videoPromises);
                setVideos(videoList);
            } catch (error) {
                console.error("Error fetching videos:", error);
                setError("Failed to load videos");
            } finally {
                setLoading(false);
            }
        };

        fetchAllVideos();
    }, [user]);

    const handleVideoClick = (video) => {
        setSelectedVideo(video);
        setShowModal(true);
    };

    const closeModal = () => {
        setShowModal(false);
        setSelectedVideo(null);
    };

    // Main app layout with separated header
    return (
        <>
            {/* Main application header - outside of the dashboard container */}
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
        <button className="logout-button" onClick={() => {
  logout();
  navigate('/');
}}>Logout</button>
      </div>
    ) : (
      <button className="login-button" onClick={() => navigate("/")}>
        Login
      </button>
    )}
  </div>
</header>

            {/* Dashboard content area */}
            <div className="video-dashboard">
                <div className="dashboard-header">
                    <button className="back-button" onClick={() => navigate(-1)}>
                        &larr; Back
                    </button>
                    <h2>All Optimized Videos</h2>
                </div>
                
                {loading && (
                    <div className="loading-container">
                        <div className="loading-spinner"></div>
                        <p>Loading your videos...</p>
                    </div>
                )}
                
                {error && (
                    <div className="error-container">
                        <p>{error}</p>
                        <button onClick={() => window.location.reload()}>Try Again</button>
                    </div>
                )}
                
                {!loading && !error && videos.length === 0 && (
                    <div className="empty-state">
                        <p>No videos found. Upload your first video to get started!</p>
                    </div>
                )}
                
                {!loading && !error && videos.length > 0 && (
                    <div className="video-grid">
                        {videos.map((video) => (
                            <div
                                key={video.id}
                                className="video-card"
                                onClick={() => handleVideoClick(video)}
                            >
                                <img
                                    src={video.thumbnailUrl}
                                    alt={video.title}
                                    className="video-thumbnail"
                                />
                                <p className="video-title">{video.title}</p>
                                {video.timestamp && (
                                    <p className="video-date">
                                        {new Date(video.timestamp.seconds * 1000).toLocaleDateString()}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                )}
                
                {showModal && selectedVideo && (
                    <VideoDetails 
                        onClose={closeModal} 
                        videoTitle={selectedVideo.videoTitle}
                    />
                )}
            </div>
        </>
    );
};

export default AllVideosPage;