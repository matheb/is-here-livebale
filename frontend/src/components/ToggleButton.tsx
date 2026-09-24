import React, { useState } from "react";

interface ToggleButtonProps {
  /** Initial selection state. */
  selected?: boolean;
  /** The text to display on the button. */
  label: string;
  /** Callback function triggered when the toggle state changes. */
  onToggle?: (isSelected: boolean) => void;
}

/**
 * A toggle button component that uses Calcite Design System.
 * It manages its own internal state for selection.
 */
export const ToggleButton: React.FC<ToggleButtonProps> = ({
  selected = false,
  label,
  onToggle,
}) => {
  const [isSelected, setIsSelected] = useState(selected);

  const handleToggle = () => {
    const newState = !isSelected;
    setIsSelected(newState);
    if (onToggle) {
      onToggle(newState);
    }
  };

  return (
    <calcite-button appearance={isSelected ? "solid" : "outline"} onClick={handleToggle}>
      {label}
    </calcite-button>
  );
};

export default ToggleButton;
