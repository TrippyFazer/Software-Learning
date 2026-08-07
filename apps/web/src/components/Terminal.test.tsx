import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import type { TermState } from "../types";
import Terminal from "./Terminal";

const state: TermState = {
  cwd: "/home/learner/projects",
  transcript: [
    { input: "mkdir projects", output: [], cwd_after: "/home/learner" },
    { input: "ls", output: ["projects/"], cwd_after: "/home/learner" },
  ],
  goals: [],
  completed: false,
};

test("renders transcript inputs and outputs", () => {
  render(<Terminal state={state} busy={false} onInput={() => {}} />);
  expect(screen.getByText(/mkdir projects/)).toBeInTheDocument();
  expect(screen.getByText("projects/")).toBeInTheDocument();
});

test("prompt shows shortened cwd with ~ substitution", () => {
  render(<Terminal state={state} busy={false} onInput={() => {}} />);
  // form prompt reflects current cwd: /home/learner/projects → ~/projects
  expect(screen.getByText("learner@lab:~/projects$")).toBeInTheDocument();
});

test("submitting the input line calls onInput and clears the field", async () => {
  const user = userEvent.setup();
  const onInput = vi.fn();
  render(<Terminal state={state} busy={false} onInput={onInput} />);
  const input = screen.getByLabelText("terminal input");
  await user.type(input, "ls -l{Enter}");
  expect(onInput).toHaveBeenCalledWith("ls -l");
  expect(input).toHaveValue("");
});

test("input is disabled while busy", () => {
  render(<Terminal state={state} busy={true} onInput={() => {}} />);
  expect(screen.getByLabelText("terminal input")).toBeDisabled();
});
