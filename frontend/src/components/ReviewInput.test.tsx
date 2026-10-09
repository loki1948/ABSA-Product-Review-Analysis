import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import ReviewInput, { EXAMPLES } from "./ReviewInput";

function Harness({
  onSubmit = () => {},
  busy = false,
  disabledReason,
  initial = "",
}: {
  onSubmit?: () => void;
  busy?: boolean;
  disabledReason?: string;
  initial?: string;
}) {
  const [value, setValue] = useState(initial);
  const [save, setSave] = useState(true);
  return (
    <ReviewInput
      value={value}
      onChange={setValue}
      save={save}
      onSaveChange={setSave}
      onSubmit={onSubmit}
      busy={busy}
      disabledReason={disabledReason}
    />
  );
}

describe("ReviewInput", () => {
  it("counts characters against the limit", async () => {
    render(<Harness />);
    expect(screen.getByText("0 / 5000")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/product review/i), "Great");
    expect(screen.getByText("5 / 5000")).toBeInTheDocument();
  });

  it("cannot be submitted while the review is blank", async () => {
    render(<Harness />);
    const button = screen.getByRole("button", { name: /analyze review/i });
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/product review/i), "   ");
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/product review/i), "ok");
    expect(button).toBeEnabled();
  });

  it("fills the box from an example", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: EXAMPLES[1].label }));
    expect(screen.getByLabelText(/product review/i)).toHaveValue(EXAMPLES[1].text);
  });

  it("submits with the button and with Ctrl+Enter", async () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} initial="Great screen" />);
    await userEvent.click(screen.getByRole("button", { name: /analyze review/i }));
    await userEvent.type(screen.getByLabelText(/product review/i), "{Control>}{Enter}{/Control}");
    expect(onSubmit).toHaveBeenCalledTimes(2);
  });

  it("shows progress and blocks a second submit while busy", () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} busy initial="Great screen" />);
    expect(screen.getByRole("button", { name: /analyzing/i })).toBeDisabled();
  });

  it("is disabled with an explanation when analysis is unavailable", () => {
    render(<Harness initial="Great screen" disabledReason="The models are not loaded." />);
    expect(screen.getByRole("button", { name: /analyze review/i })).toBeDisabled();
    expect(screen.getByText("The models are not loaded.")).toBeInTheDocument();
  });
});
