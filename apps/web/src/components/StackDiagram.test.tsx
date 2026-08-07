import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import StackDiagram from "./StackDiagram";

const nodes = [
  { label: "Browser", detail: "The client." },
  { label: "Caddy", detail: "The reverse proxy." },
];

test("renders all nodes with arrows between them", () => {
  render(<StackDiagram nodes={nodes} />);
  expect(screen.getByText("Browser")).toBeInTheDocument();
  expect(screen.getByText("Caddy")).toBeInTheDocument();
  expect(screen.getByText("↓")).toBeInTheDocument(); // one arrow for two nodes
});

test("clicking a node reveals its explanation; clicking again hides it", async () => {
  const user = userEvent.setup();
  render(<StackDiagram nodes={nodes} />);
  expect(screen.queryByText("The reverse proxy.")).not.toBeInTheDocument();

  await user.click(screen.getByText("Caddy"));
  expect(screen.getByText("The reverse proxy.")).toBeInTheDocument();

  await user.click(screen.getByText("Caddy"));
  expect(screen.queryByText("The reverse proxy.")).not.toBeInTheDocument();
});

test("only one node's detail is open at a time", async () => {
  const user = userEvent.setup();
  render(<StackDiagram nodes={nodes} />);
  await user.click(screen.getByText("Browser"));
  await user.click(screen.getByText("Caddy"));
  expect(screen.queryByText("The client.")).not.toBeInTheDocument();
  expect(screen.getByText("The reverse proxy.")).toBeInTheDocument();
});
