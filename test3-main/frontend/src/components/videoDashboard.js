import React, { useEffect, useState, useContext } from "react";
import { collection, getDocs } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import { useNavigate } from "react-router-dom";
import "./videoDashboard.css";

const VideoDashboard = () => {
    const { user } = useContext(UserContext);
    const [videos, setVideos] = useState([]);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchVideos = async () => {
            if (!user || !user.uid) return;
            
            try {
                // Get all video folders within the user's videos collection
                const videosCollectionRef = collection(db, "users", user.uid, "videos");
                const videoFoldersSnapshot = await getDocs(videosCollectionRef);
                
                const videoList = [];
                
                // For each video folder, fetch the metadata
                for (const videoFolder of videoFoldersSnapshot.docs) {
                    const videoTitle = videoFolder.id;
                    const metadataCollectionRef = collection(
                        db, 
                        "users", 
                        user.uid, 
                        "videos", 
                        videoTitle, 
                        "fetchedVideos"
                    );
                    
                    const metadataSnapshot = await getDocs(metadataCollectionRef);
                    
                    metadataSnapshot.docs.forEach(doc => {
                        videoList.push({
                            id: doc.id,
                            videoTitle: videoTitle,
                            ...doc.data()
                        });
                    });
                }
                
                setVideos(videoList);
            } catch (error) {
                console.error("Error fetching videos:", error);
            }
        };

        fetchVideos();
    }, [user]);

    return (
        <div className="video-dashboard">
            <h6>My Recent Projects</h6>
            <div className="video-grid">
                {videos.map((video) => (
                    <div
                        key={video.id}
                        className="video-card"
                        onClick={() =>
                            navigate(`/video/${video.id}/${user.uid}`, {
                                state: {
                                    userId: user.uid,
                                    videoRef: video,
                                    videoTitle: video.videoTitle,
                                },
                            })
                        }
                    >
                        <img
                            src={video.thumbnailUrl}
                            alt={video.title}
                            className="video-thumbnail"
                        />
                        <p>{video.title}</p>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default VideoDashboard;