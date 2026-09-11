import { supabase } from "./api.js";

const form = document.getElementById("auth-form");
const loginBtn = document.getElementById("login-btn");
const signupBtn = document.getElementById("signup-btn");
const errorMsg = document.getElementById("error-msg");

function showError(message) {
  errorMsg.textContent = message;
}

const { data: existingSession } = await supabase.auth.getSession();
if (existingSession?.session) {
  window.location.href = "/dashboard";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault(); // log in on plain form submit
  await handleLogin();
});

signupBtn.addEventListener("click", async () => {
  await handleSignup();
});

async function handleLogin() {
  showError("");
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  const { error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    showError(error.message);
    return;
  }

  window.location.href = "/dashboard";
}

async function handleSignup() {
  showError("");
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  const { error } = await supabase.auth.signUp({ email, password });

  if (error) {
    showError(error.message);
    return;
  }

  showError("Signed up — check your email to confirm, then log in.");
}