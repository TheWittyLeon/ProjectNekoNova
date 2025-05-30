import React, { useState, useEffect } from "react";

const BotControlPage = () => {
  const [botStatus, setBotStatus] = useState("Checking...");
  const [isBotActive, setIsBotActive] = useState(false);

  //const currentHost = "http://10.69.69.128:8080";
  const currentHost = "http://10.69.69.122:8080";
  //const currentHost = process.env.REACT_APP_CURRENT_HOST;

  // Fetch bot status on page load
  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const response = await fetch(`${currentHost}/bot/status`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      if (data.status === "active") {
        setBotStatus("Active");
        setIsBotActive(true);
      } else if (data.status === "inactive") {
        setBotStatus("Inactive");
        setIsBotActive(false);
      } else {
        setBotStatus("Not initialized");
      }
    } catch (error) {
      console.error("Error checking status:", error);
      setBotStatus(`Error: ${error.message}`);
    }
  };

  const controlBot = async (action) => {
    try {
      const response = await fetch(`${currentHost}/bot/control`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ action }), // Ensure this matches the backend's expected format
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Unknown error");
      }
      const data = await response.json();
      checkStatus();
    } catch (error) {
      console.error(`Error with ${action} command:`, error);
      alert(`Error: ${error.message}`);
    }
  };

  return (
    <div style={styles.container}>
      <h1>Suzu Twitch Bot Control Panel</h1>
      <div style={styles.controlPanel}>
        <div style={styles.status}>
          Status:{" "}
          <span style={isBotActive ? styles.active : styles.inactive}>
            {botStatus}
          </span>
        </div>
        <button
          style={styles.button}
          onClick={() => controlBot("start")}
          disabled={isBotActive}
        >
          Start Bot
        </button>
        <button
          style={{ ...styles.button, ...styles.stopButton }}
          onClick={() => controlBot("stop")}
          disabled={!isBotActive}
        >
          Stop Bot
        </button>
        <button style={styles.button} onClick={checkStatus}>
          Refresh Status
        </button>
      </div>
    </div>
  );
};

const styles = {
  container: {
    fontFamily: "Arial, sans-serif",
    maxWidth: "800px",
    margin: "0 auto",
    padding: "20px",
  },
  controlPanel: {
    backgroundColor: "#f5f5f5",
    borderRadius: "8px",
    padding: "20px",
    marginTop: "20px",
  },
  status: {
    fontSize: "18px",
    marginBottom: "20px",
  },
  active: {
    color: "green",
    fontWeight: "bold",
  },
  inactive: {
    color: "red",
    fontWeight: "bold",
  },
  button: {
    backgroundColor: "#4CAF50",
    border: "none",
    color: "white",
    padding: "10px 20px",
    textAlign: "center",
    textDecoration: "none",
    display: "inline-block",
    fontSize: "16px",
    margin: "4px 2px",
    cursor: "pointer",
    borderRadius: "4px",
  },
  stopButton: {
    backgroundColor: "#f44336",
  },
};

export default BotControlPage;