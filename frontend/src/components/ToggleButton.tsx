import React, { useState } from "react";

interface ToggleButtonProps {
  /** Initial selection state. */
  selected?: boolean;
  /** The text to display on the button. */
  label: string;
  /** Callback function triggered when the toggle state changes. */
  onToggle?: (isSelected: boolean) => void;
  /** Loading state to show a spinner on the button. */
  loading?: boolean;
}

/**
 * A toggle button component that uses Calcite Design System.
 * It manages its own internal state for selection.
 */
export const ToggleButton: React.FC<ToggleButtonProps> = ({
  selected = false,
  label,
  onToggle,
  loading = false,
}) => {
  const [isSelected, setIsSelected] = useState(selected);

  // Sync internal state with the 'selected' prop
  React.useEffect(() => {
    setIsSelected(selected);
  }, [selected]);

  const handleToggle = () => {
    const newState = !isSelected;
    setIsSelected(newState);
    if (onToggle) {
      onToggle(newState);
    }
  };

  return (
    <calcite-button
      appearance={isSelected ? "solid" : "outline"}
      onClick={handleToggle}
      loading={loading}
    >
      {label}
    </calcite-button>
  );
};

export default ToggleButton;
