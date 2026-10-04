"use client";

import { type FormEvent, useState } from "react";
import { Check, LockKeyhole, Mail, ShieldCheck, UserRound } from "lucide-react";

import { useMemberAccount } from "@/components/member-workspace";
import { ApiError, changeMyPassword, updateMyProfile } from "@/lib/api";

export default function MemberAccountPage() {
  const { account, setAccount } = useMemberAccount();
  const [displayName, setDisplayName] = useState(account.display_name);
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileMessage, setProfileMessage] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setProfileBusy(true);
    setProfileError("");
    setProfileMessage("");
    try {
      const result = await updateMyProfile({ display_name: displayName });
      setAccount(result.user);
      setDisplayName(result.user.display_name);
      setProfileMessage("Your profile has been updated.");
    } catch (error) {
      setProfileError(error instanceof ApiError ? error.message : "Your profile could not be updated.");
    } finally {
      setProfileBusy(false);
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordError("");
    setPasswordMessage("");
    if (newPassword !== confirmPassword) {
      setPasswordError("The new passwords do not match.");
      return;
    }
    setPasswordBusy(true);
    try {
      const result = await changeMyPassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMessage(result.detail);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      setPasswordError(error instanceof ApiError ? error.message : "Your password could not be changed.");
    } finally {
      setPasswordBusy(false);
    }
  }

  return (
    <div className="member-page">
      <header className="member-page-heading">
        <div>
          <p className="eyebrow">Your profile</p>
          <h1>Account settings</h1>
          <p>Manage your personal details and keep your sign-in secure.</p>
        </div>
        <span className="member-heading-icon"><UserRound size={22} /></span>
      </header>

      <section className="member-settings-card">
        <div className="member-settings-card__intro">
          <span className="member-settings-icon"><UserRound size={18} /></span>
          <div><h2>Personal details</h2><p>These details identify your member account.</p></div>
        </div>
        <form className="member-settings-form" onSubmit={saveProfile}>
          <label className="field-label" htmlFor="member-display-name">Display name
            <span className="member-input-icon"><UserRound size={16} /><input className="field-input" id="member-display-name" name="display_name" autoComplete="name" maxLength={120} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></span>
          </label>
          <label className="field-label" htmlFor="member-email">Email address
            <span className="member-input-icon"><Mail size={16} /><input className="field-input" id="member-email" name="email" type="email" autoComplete="email" value={account.email} readOnly aria-describedby="member-email-note" /></span>
          </label>
          <p className="member-field-note" id="member-email-note">Email changes are disabled until account verification is available.</p>
          {profileError && <p className="auth-error" role="alert">{profileError}</p>}
          {profileMessage && <p className="member-success" role="status"><Check size={15} />{profileMessage}</p>}
          <button className="button button--forest member-form-submit" type="submit" disabled={profileBusy}>
            {profileBusy ? "Saving…" : "Save profile"}
          </button>
        </form>
      </section>

      <section className="member-settings-card">
        <div className="member-settings-card__intro">
          <span className="member-settings-icon"><LockKeyhole size={18} /></span>
          <div><h2>Change password</h2><p>Choose a unique password you do not use elsewhere.</p></div>
        </div>
        <form className="member-settings-form" onSubmit={updatePassword}>
          <label className="field-label" htmlFor="current-password">Current password
            <input className="field-input" id="current-password" name="current_password" type="password" autoComplete="current-password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
          </label>
          <div className="member-settings-form__row">
            <label className="field-label" htmlFor="new-password">New password
              <input className="field-input" id="new-password" name="new_password" type="password" autoComplete="new-password" minLength={8} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
            </label>
            <label className="field-label" htmlFor="confirm-password">Confirm new password
              <input className="field-input" id="confirm-password" name="confirm_password" type="password" autoComplete="new-password" minLength={8} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
            </label>
          </div>
          {passwordError && <p className="auth-error" role="alert">{passwordError}</p>}
          {passwordMessage && <p className="member-success" role="status"><Check size={15} />{passwordMessage}</p>}
          <button className="button button--forest member-form-submit" type="submit" disabled={passwordBusy}>
            {passwordBusy ? "Updating…" : "Update password"}
          </button>
        </form>
      </section>

      <p className="member-security-note"><ShieldCheck size={16} /> Your password is verified and changed securely. It is never displayed or saved in this browser.</p>
    </div>
  );
}
