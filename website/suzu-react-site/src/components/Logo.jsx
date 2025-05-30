/**
 * Renders the logo component, which displays the GSU logo.
 * @returns {JSX.Element} The logo component.
 */
import SuzuIcon from "../images/suzuicon.png";
const Logo = () => {
  return (
    <div className="logo">
      <div className="logo-icon" style={{ width: "50px", height: "50px" }}>
        <img
          src={SuzuIcon}
          style={{ width: "150%", height: "140%", objectFit: "contain" }}
        />
      </div>
    </div>
  );
};

export default Logo;
