document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("menu-btn");
  const side = document.getElementById("sidebar");
  if (btn && side) btn.addEventListener("click", () => side.classList.toggle("open"));
  // auto-dismiss success messages
  document.querySelectorAll(".alert-success").forEach(el => setTimeout(() => el.remove(), 4500));
});
