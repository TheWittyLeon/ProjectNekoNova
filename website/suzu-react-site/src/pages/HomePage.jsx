import React from "react";
import suzuImage from "../images/suzuimage.webp"; // Adjust the path if needed

function HomePage() {
  return (
    <div style={styles.container}>
      {/* Header Section */}
      <header style={styles.header}>
        <h1>Welcome to Suzu AI Assistant</h1>
        <p>Your personal assistant and chatbot!</p>
      </header>

      {/* Image Section */}
      <div style={styles.imageContainer}>
        <img
          src={
            suzuImage
          } // Ensure the image path is correct
          alt="Suzu AI Assistant"
          style={styles.image}
        />
      </div>
    </div>
  );
}

const styles = {
  container: {
    fontFamily: "'Arial', sans-serif",
    textAlign: "center",
    padding: "0px",
    backgroundColor: "#f9f9f9",
    color: "#333",
  },
  header: {
    marginBottom: "10px",
  },
  imageContainer: {
    margin: "10px auto",
    maxWidth: "90%",
    maxHeight: "80vh", // Ensure the image doesn't overflow the viewport
  },
  image: {
    width: "100%",
    height: "auto",
    borderRadius: "10px",
    boxShadow: "0 4px 8px rgba(0, 0, 0, 0.1)",
  },
};

export default HomePage;