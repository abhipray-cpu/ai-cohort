import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import ChatApp from "./ChatApp";
import "./styles.css";

function Product() {
  const [hash, setHash] = React.useState(window.location.hash);
  React.useEffect(() => {
    const change = () => setHash(window.location.hash);
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  return hash === "#knowledge" || hash === "#workspace" ? (
    <App key={hash} />
  ) : (
    <ChatApp />
  );
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Product />
  </React.StrictMode>,
);
