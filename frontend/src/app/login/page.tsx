"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BrainCircuit, Lock } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

const API_BASE = "";

const ERROR_MESSAGES: Record<string, string> = {
  oauth_failed: "Google sign-in failed. Please try again.",
  domain_not_allowed: "Only users from your organisation's domain are allowed.",
  invalid_credentials: "Invalid admin credentials.",
};

function LoginContent() {
  const params = useSearchParams();
  const error = params.get("error");
  const [showAdmin, setShowAdmin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [adminError, setAdminError] = useState("");
  const [loading, setLoading] = useState(false);
  const qc = useQueryClient();

  async function handleAdminLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setAdminError("");
    try {
      const res = await fetch("/api/auth/admin-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        setAdminError("Invalid admin credentials.");
        return;
      }
      await qc.invalidateQueries({ queryKey: ["auth", "me"] });
      window.location.href = "/admin";
    } catch {
      setAdminError("Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="h-14 w-14 rounded-2xl bg-brand-500 flex items-center justify-center mb-4 shadow-lg shadow-brand-500/25">
            <BrainCircuit className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Engineering Command Center</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            {showAdmin ? "Admin sign in" : "Sign in with your account"}
          </p>
        </div>

        {/* Error from OAuth redirect */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400 text-center">
            {ERROR_MESSAGES[error] ?? "An error occurred. Please try again."}
          </div>
        )}

        {!showAdmin ? (
          <>
            {/* Google sign in */}
            <a
              href={`${API_BASE}/api/v1/auth/login`}
              className="flex items-center justify-center gap-3 w-full px-4 py-3 rounded-xl
                         bg-white dark:bg-[var(--bg-secondary)] border border-[var(--border)]
                         text-[var(--text-primary)] font-medium text-sm
                         hover:bg-[var(--bg-hover)] transition-colors shadow-sm"
            >
              <GoogleIcon />
              Continue with Google
            </a>
            <p className="text-center text-xs text-[var(--text-muted)] mt-6">
              Access restricted to your organisation's domain
            </p>
            <div className="text-center mt-4">
              <button
                onClick={() => setShowAdmin(true)}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
              >
                Admin login
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Admin login form */}
            <form onSubmit={handleAdminLogin} className="space-y-3">
              {adminError && (
                <div className="px-4 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400 text-center">
                  {adminError}
                </div>
              )}
              <input
                type="email"
                placeholder="Admin email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)]
                           text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)]
                           focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border)]
                           text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)]
                           focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="flex items-center justify-center gap-2 w-full px-4 py-3 rounded-xl
                           bg-brand-500 text-white font-medium text-sm
                           hover:bg-brand-600 transition-colors disabled:opacity-50"
              >
                <Lock className="h-4 w-4" />
                {loading ? "Signing in…" : "Sign in as Admin"}
              </button>
            </form>
            <div className="text-center mt-4">
              <button
                onClick={() => setShowAdmin(false)}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
              >
                ← Back to Google sign in
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--bg-primary)]" />}>
      <LoginContent />
    </Suspense>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
      <path d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 6.293C4.672 4.166 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  );
}
