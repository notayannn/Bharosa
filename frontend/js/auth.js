import { supabase } from "./api.js";

const form = document.getElementById("auth-form");
const errorMsg = document.getElementById("error-msg");
const loginBtn = document.getElementById("login-btn");
const tabLogin = document.getElementById("tab-login");
const tabSignup = document.getElementById("tab-signup");
const title = document.getElementById("auth-title");
const tagline = document.getElementById("auth-tagline");
const signupFields = document.getElementById("signup-only-fields");
const confirmField = document.getElementById("confirm-password-field");
const switchHint = document.getElementById("auth-switch-hint");

let mode = "login";

function showError(message) {
  errorMsg.textContent = message;
}

function setMode(newMode) {
  mode = newMode;
  showError("");
  if (mode === "login") {
    tabLogin.classList.add("active");
    tabSignup.classList.remove("active");
    title.textContent = "Welcome back";
    tagline.textContent = "Log in to your ledger.";
    loginBtn.textContent = "Log in";
    signupFields.style.display = "none";
    confirmField.style.display = "none";
    switchHint.innerHTML = `Don't have an account? <a href="#" id="switch-to-signup">Sign up</a>`;
  } else {
    tabSignup.classList.add("active");
    tabLogin.classList.remove("active");
    title.textContent = "Create your account";
    tagline.textContent = "Set up your business on Bharosa.";
    loginBtn.textContent = "Create account";
    signupFields.style.display = "flex";
    confirmField.style.display = "flex";
    switchHint.innerHTML = `Already have an account? <a href="#" id="switch-to-login">Log in</a>`;
  }
  attachSwitchLink();
}

function attachSwitchLink() {
  const link = document.getElementById(mode === "login" ? "switch-to-signup" : "switch-to-login");
  link?.addEventListener("click", (e) => {
    e.preventDefault();
    setMode(mode === "login" ? "signup" : "login");
  });
}

tabLogin.addEventListener("click", () => setMode("login"));
tabSignup.addEventListener("click", () => setMode("signup"));
attachSwitchLink();

const { data: existingSession } = await supabase.auth.getSession();
if (existingSession?.session) {
  window.location.href = "/dashboard";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (mode === "login") await handleLogin();
  else await handleSignup();
});

async function handleLogin() {
  showError("");
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  if (!email || !password) {
    showError("Enter an email and password first.");
    return;
  }

  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    showError(error.message);
    return;
  }
  window.location.href = "/dashboard";
}

async function handleSignup() {
  showError("");
  const fullName = document.getElementById("full-name").value.trim();
  const businessName = document.getElementById("business-name-signup").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirm-password").value;

  if (!fullName || !businessName || !email || !password) {
    showError("Fill in every field to create your account.");
    return;
  }
  if (password !== confirmPassword) {
    showError("Passwords don't match.");
    return;
  }
  if (password.length < 6) {
    showError("Password needs to be at least 6 characters.");
    return;
  }

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { full_name: fullName, pending_business_name: businessName } },
  });
  if (error) {
    showError(error.message);
    return;
  }
  showError("Account created — check your email to confirm, then log in.");
}