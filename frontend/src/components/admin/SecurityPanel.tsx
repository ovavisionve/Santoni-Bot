"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { User } from "@/types";
import {
  Shield,
  ShieldCheck,
  KeyRound,
  QrCode,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
  Unlock,
} from "lucide-react";

export default function SecurityPanel({ user }: { user: User }) {
  const [totpSetup, setTotpSetup] = useState<{
    secret: string;
    qr_uri: string;
  } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [totpMessage, setTotpMessage] = useState("");
  const [totpError, setTotpError] = useState("");
  const [totpEnabled, setTotpEnabled] = useState(user.totp_enabled);
  const [loadingTotp, setLoadingTotp] = useState(false);

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwMessage, setPwMessage] = useState("");
  const [pwError, setPwError] = useState("");
  const [loadingPw, setLoadingPw] = useState(false);

  const [secOverview, setSecOverview] = useState<{
    failed_logins_24h: number;
    account_lockouts_7d: number;
    currently_locked: number;
    totp_enabled_users: number;
    total_active_users: number;
    totp_coverage_pct: number;
    suspicious_ips: Array<{ ip: string; failed_attempts: number }>;
  } | null>(null);
  const [lockedUsers, setLockedUsers] = useState<
    Array<{
      id: number;
      username: string;
      full_name: string;
      department: string;
      failed_attempts: number;
      remaining_minutes: number;
    }>
  >([]);

  useEffect(() => {
    loadSecurityData();
  }, []);

  const loadSecurityData = async () => {
    try {
      const [overview, locked] = await Promise.all([
        api.getSecurityOverview(),
        api.getLockedUsers(),
      ]);
      setSecOverview(overview);
      setLockedUsers(locked);
    } catch {
      // ignore if not admin
    }
  };

  const handleUnlock = async (userId: number) => {
    try {
      await api.unlockUser(userId);
      loadSecurityData();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error al desbloquear");
    }
  };

  const handleSetupTotp = async () => {
    setTotpError("");
    setTotpMessage("");
    setLoadingTotp(true);
    try {
      const data = await api.totpSetup();
      setTotpSetup(data);
    } catch (err) {
      setTotpError(
        err instanceof Error ? err.message : "Error al configurar 2FA"
      );
    } finally {
      setLoadingTotp(false);
    }
  };

  const handleEnableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpError("");
    setLoadingTotp(true);
    try {
      const res = await api.totpEnable(totpCode);
      setTotpMessage(res.message);
      setTotpEnabled(true);
      setTotpSetup(null);
      setTotpCode("");
    } catch (err) {
      setTotpError(
        err instanceof Error ? err.message : "Código incorrecto"
      );
    } finally {
      setLoadingTotp(false);
    }
  };

  const handleDisableTotp = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpError("");
    setLoadingTotp(true);
    try {
      const res = await api.totpDisable(disableCode);
      setTotpMessage(res.message);
      setTotpEnabled(false);
      setDisableCode("");
    } catch (err) {
      setTotpError(
        err instanceof Error ? err.message : "Código incorrecto"
      );
    } finally {
      setLoadingTotp(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError("");
    setPwMessage("");

    if (newPw !== confirmPw) {
      setPwError("Las contraseñas no coinciden");
      return;
    }

    setLoadingPw(true);
    try {
      const res = await api.changePassword(currentPw, newPw);
      setPwMessage(res.message);
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err) {
      setPwError(
        err instanceof Error ? err.message : "Error al cambiar contraseña"
      );
    } finally {
      setLoadingPw(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Security Overview (IT Dashboard) */}
      {secOverview && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Shield size={20} className="text-santoni-600" />
            <h3 className="text-lg font-semibold">
              Panel de Seguridad (TI)
            </h3>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-red-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-red-600">
                {secOverview.failed_logins_24h}
              </div>
              <div className="text-xs text-red-500">
                Logins fallidos (24h)
              </div>
            </div>
            <div className="bg-orange-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-orange-600">
                {secOverview.account_lockouts_7d}
              </div>
              <div className="text-xs text-orange-500">
                Bloqueos (7 dias)
              </div>
            </div>
            <div className={`rounded-lg p-3 text-center ${secOverview.currently_locked > 0 ? "bg-red-50" : "bg-green-50"}`}>
              <div className={`text-2xl font-bold ${secOverview.currently_locked > 0 ? "text-red-600" : "text-green-600"}`}>
                {secOverview.currently_locked}
              </div>
              <div className={`text-xs ${secOverview.currently_locked > 0 ? "text-red-500" : "text-green-500"}`}>
                Cuentas bloqueadas
              </div>
            </div>
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {secOverview.totp_coverage_pct}%
              </div>
              <div className="text-xs text-blue-500">
                Usuarios con 2FA ({secOverview.totp_enabled_users}/{secOverview.total_active_users})
              </div>
            </div>
          </div>

          {secOverview.suspicious_ips.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                <AlertTriangle size={14} className="text-orange-500" />
                IPs sospechosas (ultimos 7 dias)
              </h4>
              <div className="flex flex-wrap gap-2">
                {secOverview.suspicious_ips.map((item) => (
                  <span
                    key={item.ip}
                    className="inline-flex items-center gap-1 bg-red-50 text-red-700 text-xs px-2 py-1 rounded font-mono"
                  >
                    {item.ip}
                    <span className="bg-red-200 text-red-800 px-1 rounded">
                      {item.failed_attempts}x
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Locked Users Management */}
      {lockedUsers.length > 0 && (
        <div className="bg-white rounded-xl border border-red-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <Lock size={20} className="text-red-500" />
            <h3 className="text-lg font-semibold text-red-700">
              Cuentas Bloqueadas ({lockedUsers.length})
            </h3>
          </div>
          <div className="space-y-2">
            {lockedUsers.map((lu) => (
              <div
                key={lu.id}
                className="flex items-center justify-between bg-red-50 rounded-lg px-4 py-3"
              >
                <div>
                  <span className="font-medium text-gray-900">
                    {lu.full_name}
                  </span>
                  <span className="text-gray-500 text-sm ml-2">
                    @{lu.username}
                  </span>
                  <span className="text-red-500 text-xs ml-2">
                    ({lu.failed_attempts} intentos, {lu.remaining_minutes} min restantes)
                  </span>
                </div>
                <button
                  onClick={() => handleUnlock(lu.id)}
                  className="flex items-center gap-1 bg-white border border-gray-200 text-gray-700 px-3 py-1.5 rounded-lg text-sm hover:bg-green-50 hover:border-green-300 hover:text-green-700 transition-colors"
                >
                  <Unlock size={14} />
                  Desbloquear
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2FA Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <ShieldCheck size={20} className="text-santoni-600" />
          <h3 className="text-lg font-semibold">
            Autenticación de Dos Factores (2FA)
          </h3>
          {totpEnabled ? (
            <span className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
              <CheckCircle2 size={12} /> Activo
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
              <XCircle size={12} /> Inactivo
            </span>
          )}
        </div>

        <p className="text-sm text-gray-500 mb-4">
          Agrega una capa extra de seguridad a tu cuenta usando Google
          Authenticator u otra aplicación compatible con TOTP.
        </p>

        {totpMessage && (
          <div className="bg-green-50 border border-green-200 text-green-700 text-sm p-3 rounded-lg mb-4">
            {totpMessage}
          </div>
        )}
        {totpError && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
            {totpError}
          </div>
        )}

        {!totpEnabled && !totpSetup && (
          <button
            onClick={handleSetupTotp}
            disabled={loadingTotp}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <QrCode size={16} />
            {loadingTotp ? "Generando..." : "Configurar 2FA"}
          </button>
        )}

        {!totpEnabled && totpSetup && (
          <div className="space-y-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm font-medium text-gray-700 mb-2">
                1. Escanea este código QR con Google Authenticator:
              </p>
              <div className="flex justify-center my-4">
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  {/* QR code rendered as URI - user scans with their app */}
                  <div className="text-center">
                    <QrCode size={120} className="text-gray-800 mx-auto" />
                    <p className="text-xs text-gray-500 mt-2 break-all max-w-xs">
                      {totpSetup.qr_uri}
                    </p>
                  </div>
                </div>
              </div>
              <p className="text-sm font-medium text-gray-700 mb-1">
                2. O ingresa este código manualmente:
              </p>
              <code className="block bg-white border border-gray-200 rounded px-3 py-2 text-center font-mono text-lg tracking-wider select-all">
                {totpSetup.secret}
              </code>
            </div>

            <form onSubmit={handleEnableTotp} className="flex items-end gap-3">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  3. Ingresa el código de 6 dígitos para verificar:
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) =>
                    setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  className="input-field text-center text-xl tracking-[0.4em] font-mono"
                  placeholder="000000"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loadingTotp || totpCode.length !== 6}
                className="btn-primary text-sm whitespace-nowrap"
              >
                {loadingTotp ? "Verificando..." : "Activar 2FA"}
              </button>
            </form>
          </div>
        )}

        {totpEnabled && (
          <form onSubmit={handleDisableTotp} className="flex items-end gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Para desactivar 2FA, ingresa tu código actual:
              </label>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={disableCode}
                onChange={(e) =>
                  setDisableCode(
                    e.target.value.replace(/\D/g, "").slice(0, 6)
                  )
                }
                className="input-field text-center text-xl tracking-[0.4em] font-mono"
                placeholder="000000"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loadingTotp || disableCode.length !== 6}
              className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-600 transition-colors whitespace-nowrap"
            >
              Desactivar 2FA
            </button>
          </form>
        )}
      </div>

      {/* Password Change Section */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <KeyRound size={20} className="text-santoni-600" />
          <h3 className="text-lg font-semibold">Cambiar Contraseña</h3>
        </div>

        <p className="text-sm text-gray-500 mb-4">
          La contraseña debe tener mínimo 8 caracteres, una mayúscula, una
          minúscula, un número y un carácter especial (!@#$%^&*).
        </p>

        {pwMessage && (
          <div className="bg-green-50 border border-green-200 text-green-700 text-sm p-3 rounded-lg mb-4">
            {pwMessage}
          </div>
        )}
        {pwError && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-lg mb-4">
            {pwError}
          </div>
        )}

        <form onSubmit={handleChangePassword} className="space-y-3 max-w-md">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contraseña actual
            </label>
            <input
              type="password"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nueva contraseña
            </label>
            <input
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              className="input-field"
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar nueva contraseña
            </label>
            <input
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              className="input-field"
              required
              minLength={8}
            />
          </div>
          <button
            type="submit"
            disabled={loadingPw || !currentPw || !newPw || !confirmPw}
            className="btn-primary text-sm"
          >
            {loadingPw ? "Actualizando..." : "Cambiar Contraseña"}
          </button>
        </form>
      </div>
    </div>
  );
}
