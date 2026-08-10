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

test("input stays ENABLED and focused while busy (focus must never leave the terminal)", () => {
  render(<Terminal state={state} busy={true} onInput={() => {}} />);
  const input = screen.getByLabelText("terminal input");
  expect(input).toBeEnabled();
});

test("submit is ignored while busy", async () => {
  const user = userEvent.setup();
  const onInput = vi.fn();
  render(<Terminal state={state} busy={true} onInput={onInput} />);
  await user.type(screen.getByLabelText("terminal input"), "ls{Enter}");
  expect(onInput).not.toHaveBeenCalled();
});

test("arrow-up walks back through command history, arrow-down returns to draft", async () => {
  const user = userEvent.setup();
  render(<Terminal state={state} busy={false} onInput={() => {}} />);
  const input = screen.getByLabelText("terminal input");

  await user.type(input, "dra");             // an unfinished draft line
  await user.keyboard("{ArrowUp}");          // most recent command
  expect(input).toHaveValue("ls");
  await user.keyboard("{ArrowUp}");          // older command
  expect(input).toHaveValue("mkdir projects");
  await user.keyboard("{ArrowUp}");          // at the oldest: stays put
  expect(input).toHaveValue("mkdir projects");
  await user.keyboard("{ArrowDown}");
  expect(input).toHaveValue("ls");
  await user.keyboard("{ArrowDown}");        // past the end: draft restored
  expect(input).toHaveValue("dra");
});

test("recalled history line can be submitted", async () => {
  const user = userEvent.setup();
  const onInput = vi.fn();
  render(<Terminal state={state} busy={false} onInput={onInput} />);
  const input = screen.getByLabelText("terminal input");
  await user.click(input);
  await user.keyboard("{ArrowUp}{Enter}");
  expect(onInput).toHaveBeenCalledWith("ls");
});

test("Ctrl+C abandons the current line", async () => {
  const user = userEvent.setup();
  render(<Terminal state={state} busy={false} onInput={() => {}} />);
  const input = screen.getByLabelText("terminal input");
  await user.type(input, "rm -rf importan");
  await user.keyboard("{Control>}c{/Control}");
  expect(input).toHaveValue("");
});

test("Ctrl+L clears the visible scrollback without touching history", async () => {
  const user = userEvent.setup();
  render(<Terminal state={state} busy={false} onInput={() => {}} />);
  const input = screen.getByLabelText("terminal input");
  await user.click(input);
  await user.keyboard("{Control>}l{/Control}");
  expect(screen.queryByText("projects/")).not.toBeInTheDocument();
  // history still works after clearing
  await user.keyboard("{ArrowUp}");
  expect(input).toHaveValue("ls");
});
