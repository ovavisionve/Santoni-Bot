"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Eye, EyeOff, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // TOTP state
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await api.login(
        username,
        password,
        totpRequired ? totpCode : undefined
      );
      if (result.totp_required) {
        setTotpRequired(true);
        setTotpCode("");
        setLoading(false);
        return;
      }
      router.push("/chat");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Error al iniciar sesión"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setTotpRequired(false);
    setTotpCode("");
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-santoni-50 to-santoni-100 px-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {/* Logo / Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-santoni-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-white text-3xl font-bold">S</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">SantoniBot</h1>
            <p className="text-gray-500 mt-1">
              Sistema Inteligente de Análisis
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {!totpRequired ? (
              <>
                <div>
                  <label
                    htmlFor="username"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Usuario
                  </label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="input-field"
                    placeholder="Ingrese su usuario"
                    required
                    autoFocus
                  />
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Contraseña
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="input-field pr-10"
                      placeholder="Ingrese su contraseña"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                      tabIndex={-1}
                      aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div>
                <div className="flex items-center justify-center gap-2 mb-4 text-santoni-600">
                  <ShieldCheck size={24} />
                  <span className="text-sm font-semibold">
                    Verificación en dos pasos
                  </span>
                </div>
                <p className="text-xs text-gray-500 text-center mb-4">
                  Ingrese el código de 6 dígitos de su aplicación Google
                  Authenticator
                </p>
                <label
                  htmlFor="totp"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Código de verificación
                </label>
                <input
                  id="totp"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) =>
                    setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  className="input-field text-center text-2xl tracking-[0.5em] font-mono"
                  placeholder="000000"
                  required
                  autoFocus
                  autoComplete="one-time-code"
                />
                <button
                  type="button"
                  onClick={handleBack}
                  className="text-xs text-gray-400 hover:text-santoni-600 mt-2 transition-colors"
                >
                  Volver al inicio de sesión
                </button>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={
                loading ||
                (!totpRequired && (!username || !password)) ||
                (totpRequired && totpCode.length !== 6)
              }
              className="btn-primary w-full"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {totpRequired ? "Verificando..." : "Ingresando..."}
                </span>
              ) : totpRequired ? (
                "Verificar"
              ) : (
                "Iniciar Sesión"
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-xs text-gray-400 mt-6">
            Alimentos Santoni, C.A. &mdash; Desarrollado por OVA Agency
          </p>
        </div>
      </div>
    </div>
  );
}
