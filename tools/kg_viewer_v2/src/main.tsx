import { render } from "preact";
import { App } from "./ui/App";
import "./styles/main.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");
render(<App />, root);
