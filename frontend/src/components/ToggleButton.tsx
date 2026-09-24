import React from "react";

interface ToggleButtonProps {
  /** Selection state controlled by the parent. */
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
 * This is a controlled component; its state is managed by the parent.
 */
export const ToggleButton: React.FC<ToggleButtonProps> = ({
  selected = false,
  label,
  onToggle,
  loading = false,
}) => {
  const handleToggle = () => {
    if (onToggle) {
      onToggle(!selected);
    }
  };

  return (
    <calcite-button
      appearance={selected ? "solid" : "outline"}
      onClick={handleToggle}
      loading={loading}
      style={{
        borderRadius: "20px",
        "--calcite-ui-button-border-radius": "20px",
        "--calcite-ui-button-border-width": "1px"
      }}
    >
      {label}
    </calcite-button>
  );
};

export default ToggleButton;
