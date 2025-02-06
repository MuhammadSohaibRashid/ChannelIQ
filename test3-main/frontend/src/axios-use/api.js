import axios from 'axios';

// Create an Axios instance with default settings
const apiClient = axios.create({
    baseURL: process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000/api', // Use environment variable for flexibility
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 1000000, // Timeout set to 10 seconds
    withCredentials: true, // Ensure credentials (cookies) are sent with requests
});

// Function to get CSRF token from the page and set it in the headers
const setCsrfToken = () => {
    const csrfTokenElement = document.querySelector('meta[name="csrf-token"]');
    if (!csrfTokenElement) {
        throw new Error("CSRF token meta tag not found. Ensure it's present in your HTML.");
    }
    const csrfToken = csrfTokenElement.getAttribute('content');
    apiClient.defaults.headers['X-CSRFToken'] = csrfToken;
};

// Call setCsrfToken on app initialization to set the token globally for Axios requests
setCsrfToken();

// Fetch video metadata
export const fetchVideoMetadata = async (url) => {
    if (!isValidYouTubeUrl(url)) {
        throw new Error("Invalid YouTube URL provided. Please enter a valid YouTube link.");
    }

    try {
        const response = await apiClient.get('/fetch-video/', {
            params: { url },
        });
        return response.data;
    } catch (error) {
        handleApiError(error, 'fetching video metadata');
    }
};

// Download and upload video to S3
export const downloadAndUploadVideo = async (url) => {
    if (!isValidYouTubeUrl(url)) {
        throw new Error("Invalid YouTube URL provided. Please enter a valid YouTube link.");
    }

    try {
        const response = await apiClient.get('/download-video/', {
            params: { url },
        });
        return response.data;
    } catch (error) {
        handleApiError(error, 'downloading and uploading video');
    }
};

// Helper function to validate YouTube URL
const isValidYouTubeUrl = (url) => {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)[\w-]{11}/;
    return regex.test(url);
};

// Centralized error handling
const handleApiError = (error, action) => {
    if (error.response) {
        // Server responded with an error status code
        throw new Error(
            `Error ${action}: ${error.response.data?.error || error.response.statusText || "Server error occurred."}`
        );
    } else if (error.request) {
        // Request was made but no response received
        throw new Error(
            `Error ${action}: No response received from the server. Please check your network connection.`
        );
    } else {
        // Something else happened
        throw new Error(`Error ${action}: ${error.message || "An unexpected error occurred."}`);
    }
};
