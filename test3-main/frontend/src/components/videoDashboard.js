import React, { useEffect, useState, useContext } from "react";
import { collection, getDocs, query, orderBy, limit } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import VideoDetails from "./videoDetails";
import "./videoDashboard.css";

const VideoDashboard = () => {
    const { user } = useContext(UserContext);
    const [videos, setVideos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedVideo, setSelectedVideo] = useState(null);
    const [showModal, setShowModal] = useState(false);

    useEffect(() => {
        const fetchVideos = async () => {
            if (!user || !user.uid) {
                setLoading(false);
                return;
            }
            
            setLoading(true);
            try {
                // Get all video folders within the user's videos collection
                const videosCollectionRef = collection(db, "users", user.uid, "videos");
                
                // Create a query that orders by timestamp (assuming this field exists) and limits results
                const videosQuery = query(
                    videosCollectionRef,
                    orderBy("timestamp", "desc"), // Show newest first
                    limit(5) // Limit to 6 recent videos
                );
                
                const videoFoldersSnapshot = await getDocs(videosQuery);
                
                // Process results with Promise.all for parallel execution
                const videoPromises = videoFoldersSnapshot.docs.map(async (videoFolder) => {
                    const videoTitle = videoFolder.id;
                    const videoData = videoFolder.data();
                    
                    // Return basic info without fetching sub-collections to improve load time
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

        fetchVideos();
    }, [user]);

    const handleVideoClick = (video) => {
        setSelectedVideo(video);
        setShowModal(true);
    };

    const closeModal = () => {
        setShowModal(false);
        setSelectedVideo(null);
    };

    if (loading) {
        return (
            <div className="video-dashboard">
                <h6>My Recent Projects</h6>
                <div className="loading-container">
                    <div className="loading-spinner"></div>
                    <p>Loading your videos...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="video-dashboard">
                <h6>My Recent Projects</h6>
                <div className="error-container">
                    <p>{error}</p>
                    <button onClick={() => window.location.reload()}>Try Again</button>
                </div>
            </div>
        );
    }

    return (
        <div className="video-dashboard">
            <h6>My Recent Projects</h6>
            {videos.length === 0 ? (
                <div className="empty-state">
                    <p>No videos found. Upload your first video to get started!</p>
                </div>
            ) : (
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
            
            {/* Render the VideoDetails modal when a video is selected */}
            {showModal && selectedVideo && (
                <VideoDetails 
                    onClose={closeModal} 
                    videoTitle={selectedVideo.videoTitle}
                />
            )}
        </div>
    );
};

export default VideoDashboard;