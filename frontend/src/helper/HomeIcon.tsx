import { divIcon } from "leaflet";
import { renderToString } from "react-dom/server";

export const CustomHomeIcon = divIcon({
  html: renderToString(
    <div
      style={{
        backgroundColor: "darkgreen",
        color: "white",
        borderRadius: "50%",
        height: "30px",
        width: "30px",
        position: "absolute",
        left: "-15px",
        top: "-15px",
        padding: "5px",
      }}
    >
      <calcite-icon icon="home" style={{ position: "absolute", left: "7px", top: "7px" }} />
    </div>,
  ),
  className: "",
});
