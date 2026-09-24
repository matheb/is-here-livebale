import React from "react";
import { CATEGORY_STYLE } from "../const/color";
import { LABEL } from "../const/text";

/**
 * A legend component that displays the amenity types and their associated colors.
 */
export const LegendControl: React.FC = () => {
  return (
    <div
      style={{
        backgroundColor: "white",
        padding: "10px",
        borderRadius: "5px",
        boxShadow: "0 0 15px rgba(0,0,0,0.2)",
        fontSize: "12px",
        lineHeight: "18px",
        color: "#555",
      }}
    >
      <div
        style={{
          fontWeight: "bold",
          marginBottom: "5px",
          borderBottom: "1px solid #ccc",
          paddingBottom: "3px",
        }}
      >
        {LABEL.legend.amenities}
      </div>
      {Object.entries(CATEGORY_STYLE).map(([key, style]) => (
        <div
          key={key}
          style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px" }}
        >
          <div
            style={{
              width: "10px",
              height: "10px",
              backgroundColor: style.color,
              borderRadius: "50%",
              border: "1px solid #999",
            }}
          />
          <span>{style.label}</span>
        </div>
      ))}
    </div>
  );
};

export default LegendControl;
