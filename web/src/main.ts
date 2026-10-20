// Operator interface entry point. Milestone 5 adds the control connection,
// deadman input, and telemetry views (docs/DESIGN.md §8.2); until then the
// page offers no controls.
const app = document.querySelector<HTMLElement>("#app");
if (app !== null) {
  app.textContent = "Operator interface not implemented yet (milestone 5).";
}
