import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage"; 
import { collection, getDocs } from "firebase/firestore";


// ✅ Replace with your Firebase config
const firebaseConfig = {
    apiKey: "AIzaSyBZ8aocP9ZyByY9wtPQPDSk36z_gOEHB6Q",
    authDomain: "channeliq-d0733.firebaseapp.com",
    projectId: "channeliq-d0733",
    storageBucket: "channeliq-d0733.appspot.com",  // Fixed typo
    messagingSenderId: "535482841072",
    appId: "1:535482841072:web:f93282b966c7323e054f35",
    clientId: "535482841072-q4t12p6mssmb7s0q7pprs9i8drcqnnbk.apps.googleusercontent.com" // ✅ Ensure it's correctly named
};

// ✅ Initialize Firebase
const app = initializeApp(firebaseConfig);

// ✅ Export Firebase services
export const auth = getAuth(app);
export const provider = new GoogleAuthProvider();
export const db = getFirestore(app);
export const storage = getStorage(app);
export const clientId = firebaseConfig.clientId; // ✅ Export the clientId

export default app;
